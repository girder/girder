#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import filtermodel, loadmodel, Resource, RestException
from girder.constants import AccessType


class Thumbnail(Resource):
    def __init__(self):
        super(Thumbnail, self).__init__()
        self.resourceName = 'thumbnail'
        self.route('POST', (), self.createThumbnail)

    @access.user
    @loadmodel(map={'fileId': 'file'}, model='file', level=AccessType.READ)
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Create a new thumbnail from an existing image file.')
        .notes('Setting a width or height parameter of 0 will preserve the '
               'original aspect ratio.')
        .param('fileId', 'The ID of the source file.')
        .param('width', 'The desired width.', required=False, dataType='int')
        .param('height', 'The desired height.', required=False, dataType='int')
        .param('crop', 'Whether to crop the image to preserve aspect ratio. '
               'Only used if both width and height parameters are nonzero.',
               dataType='boolean', required=False, default=True)
        .param('attachToId', 'The lifecycle of this thumbnail is bound to the '
               'resource specified by this ID.')
        .param('attachToType', 'The type of resource to which this thumbnail is'
               ' attached.', enum=['folder', 'user', 'collection', 'item'])
        .errorResponse()
        .errorResponse(('Write access was denied on the attach destination.',
                        'Read access was denied on the file.'), 403)
    )
    def createThumbnail(self, file, params):
        self.requireParams(('attachToId', 'attachToType'), params)

        user = self.getCurrentUser()
        width = params.get('width')
        height = params.get('height')

        if params['attachToType'] not in (
                'item', 'collection', 'user', 'folder'):
            raise RestException('You can only attach thumbnails to users, '
                                'folders, collections, or items.')

        self.model(params['attachToType']).load(
            params['attachToId'], user=user, level=AccessType.WRITE, exc=True)

        width = max(int(params.get('width', 0)), 0)
        height = max(int(params.get('height', 0)), 0)

        if not width and not height:
            raise RestException(
                'You must specify a valid width, height, or both.')

        kwargs = {
            'width': width,
            'height': height,
            'fileId': str(file['_id']),
            'crop': self.boolParam('crop', params, default=True),
            'attachToType': params['attachToType'],
            'attachToId': params['attachToId']
        }

        job = self.model('job', 'jobs').createLocalJob(
            title='Generate thumbnail for %s' % file['name'], user=user,
            type='thumbnails.create', public=False, kwargs=kwargs,
            module='girder.plugins.thumbnails.worker')

        self.model('job', 'jobs').scheduleJob(job)

        return job
