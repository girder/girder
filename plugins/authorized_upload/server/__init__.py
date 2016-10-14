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

from girder import events
from girder.api.rest import getCurrentToken, setCurrentUser
from girder.constants import TokenScope
from girder.utility.model_importer import ModelImporter

from .constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD
from .rest import AuthorizedUpload


def _authorizeInitUpload(event):
    # This relies on the fact that the REST layer caches the token on each request.
    # Update the scope, but do not save the token. We want this to only apply to
    # this request thread.
    token = getCurrentToken()
    params = event.info['params']
    tokenModel = ModelImporter.model('token')
    parentType = params.get('parentType')
    parentId = params.get('parentId', '')
    requiredScopes = {TOKEN_SCOPE_AUTHORIZED_UPLOAD, 'authorized_upload_folder_%s' % parentId}

    if parentType == 'folder' and tokenModel.hasScope(token=token, scope=requiredScopes):
        user = ModelImporter.model('user').load(token['userId'], force=True)
        setCurrentUser(user)


def _storeUploadId(event):
    """
    Called after an upload is first initialized successfully. Sets the authorized upload ID
    in the token, ensuring it can be used for only this upload.
    """
    returnVal = event.info['returnVal']
    token = getCurrentToken()
    tokenModel = ModelImporter.model('token')
    isAuthorizedUpload = tokenModel.hasScope(token, TOKEN_SCOPE_AUTHORIZED_UPLOAD)

    if isAuthorizedUpload and returnVal.get('_modelType', 'upload') == 'upload':
        token['scope'].remove(TOKEN_SCOPE_AUTHORIZED_UPLOAD)
        token['authorizedUploadId'] = returnVal['_id']
        tokenModel.save(token)


def _authorizeUploadStep(event):
    token = getCurrentToken()
    uploadId = event.info['params'].get('uploadId')

    if 'authorizedUploadId' in token and token['authorizedUploadId'] == uploadId:
        user = ModelImporter.model('user').load(token['userId'], force=True)
        setCurrentUser(user)



def _removeToken(event):
    """
    Called after an upload finishes. We check if our current token is a special
    authorized upload token, and if so, delete it.

    TODO we could alternatively keep a reference count inside each token that authorized
    more than a single upload at a time, and just decrement it here.
    """
    token = getCurrentToken()
    if 'authorizedUploadId' in token:
        ModelImporter.model('token').remove(token)


def load(info):
    name = info['name']

    events.bind('rest.post.file.before', name, _authorizeInitUpload)
    events.bind('rest.post.file.after', name, _storeUploadId)
    events.bind('rest.post.file/chunk.before', name, _authorizeUploadStep)
    events.bind('rest.post.file/completion.before', name, _authorizeUploadStep)
    events.bind('model.file.finalizeUpload.after', name, _removeToken)

    info['apiRoot'].authorized_upload = AuthorizedUpload()

