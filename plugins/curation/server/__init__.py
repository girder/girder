#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2016 Kitware Inc.
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
from girder.api.rest import Resource, loadmodel
from girder.constants import AccessType


CURATION = 'curation'

ENABLED = 'enabled'
STATUS = 'status'
REASON = 'reason'
ENABLE_USER_ID = 'enableUserId'
REQUEST_USER_ID = 'requestUserId'
REVIEW_USER_ID = 'reviewUserId'

CONSTRUCTION = 'construction'
REQUESTED = 'requested'
APPROVED = 'approved'


class CuratedFolder(Resource):

    @access.public
    @loadmodel(model='folder', level=AccessType.READ)
    @describeRoute(
        Description('Get curation details for the folder.')
        .param('id', 'The folder ID', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read permission denied on the folder.', 403)
    )
    def getCuration(self, folder, params):
        result = {
            ENABLED: False,
            STATUS: CONSTRUCTION,
        }
        result.update(folder.get(CURATION, {}))
        return result

    @access.public
    @loadmodel(model='folder', level=AccessType.READ)
    @describeRoute(
        Description('Set curation details for the folder.')
        .param('id', 'The folder ID', paramType='path')
        .param('enabled', 'Enable or disable folder curation.',
            required=False, dataType='boolean')
        .param('status', 'Set the folder curation status.',
            required=False, dataType='string')
        .param('reason', 'Set the reason for rejecting approval.',
            required=False, dataType='string')
        .errorResponse('ID was invalid.')
        .errorResponse('Write permission denied on the folder.', 403)
    )
    def setCuration(self, folder, params):
        user = self.getCurrentUser()
        if CURATION not in folder:
            folder[CURATION] = {}
        curation = folder[CURATION]

        oldEnabled = curation.get(ENABLED, False)
        if ENABLED in params:
            self.requireAdmin(user)
            curation[ENABLED] = self.boolParam(ENABLED, params)
        enabled = curation.get(ENABLED, False)

        oldStatus = curation.get(STATUS)
        if STATUS in params:
            # regular users can only do construction -> requested transition
            if curation.get(STATUS) != CONSTRUCTION or \
               params[STATUS] != REQUESTED:
                self.requireAdmin(user)
            curation[STATUS] = params[STATUS]
        status = curation.get(STATUS)

        # admin enabling curation
        if enabled and not oldEnabled:
            # TODO: check writers exist?
            # TODO: email writers
            curation[ENABLE_USER_ID] = user.get('_id')

        # user requesting approval
        if enabled and oldStatus == CONSTRUCTION and status == REQUESTED:
            # TODO: email ENABLE_USER_ID
            curation[REQUEST_USER_ID] = user.get('_id')
            for doc in folder['access']['users'] + folder['access']['groups']:
                if doc['level'] == AccessType.WRITE:
                    doc['level'] = AccessType.READ

        # admin approving request
        if enabled and oldStatus == REQUESTED and status == APPROVED:
            # TODO: email REQUEST_USER_ID
            folder['public'] = True
            curation[REVIEW_USER_ID] = user.get('_id')

        # admin rejecting request
        if enabled and oldStatus == REQUESTED and status == CONSTRUCTION:
            # TODO: email REQUEST_USER_ID
            curation[REVIEW_USER_ID] = user.get('_id')
            curation[REASON] = params.get(REASON, '')
            for doc in folder['access']['users'] + folder['access']['groups']:
                if doc['level'] == AccessType.READ:
                    doc['level'] = AccessType.WRITE

        self.model('folder').save(folder)
        return curation


def load(info):
    curatedFolder = CuratedFolder()
    info['apiRoot'].folder.route(
        'GET', (':id', 'curation'), curatedFolder.getCuration)
    info['apiRoot'].folder.route(
        'PUT', (':id', 'curation'), curatedFolder.setCuration)
