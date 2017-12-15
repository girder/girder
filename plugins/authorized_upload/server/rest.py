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
from girder.api.describe import describeRoute, Description
from girder.api.rest import loadmodel, Resource
from girder.constants import AccessType, SettingKey, TokenScope
from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.models.token import Token
from girder.utility import mail_utils

from .constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD


class AuthorizedUpload(Resource):
    def __init__(self):
        super(AuthorizedUpload, self).__init__()
        self.resourceName = 'authorized_upload'

        self.route('POST', (), self.createAuthorizedUpload)

    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(map={'folderId': 'folder'}, model='folder', level=AccessType.WRITE)
    @describeRoute(
        Description('Create an authorized upload URL.')
        .param('folderId', 'Destination folder ID for the upload.')
        .param('duration', 'How many days the token should last.', required=False, dataType='int')
    )
    def createAuthorizedUpload(self, folder, params):
        try:
            if params.get('duration'):
                days = int(params.get('duration'))
            else:
                days = Setting().get(SettingKey.COOKIE_LIFETIME)
        except ValueError:
            raise ValidationException('Token duration must be an integer, or leave it empty.')

        token = Token().createToken(days=days, user=self.getCurrentUser(), scope=(
            TOKEN_SCOPE_AUTHORIZED_UPLOAD, 'authorized_upload_folder_%s' % folder['_id']))

        url = '%s#authorized_upload/%s/%s' % (
            mail_utils.getEmailUrlPrefix(), folder['_id'], token['_id'])

        return {'url': url}
