import os
from pathlib import Path

from bson.objectid import ObjectId
from bson.errors import InvalidId
from girder import events
from girder.api import access
from girder.api.rest import getCurrentToken, setCurrentUser
from girder.models.item import Item
from girder.models.token import Token
from girder.models.user import User
from girder.plugin import GirderPlugin, registerPluginStaticContent
from girder.utility import mail_utils

from .constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD
from .rest import AuthorizedUpload

_HERE = os.path.abspath(os.path.dirname(__file__))


@access.public
def _authorizeInitUpload(event):
    """
    Called when initializing an upload, prior to the default handler. Checks if
    the user is passing an authorized upload token, and if so, sets the current
    request-thread user to be whoever created the token.
    """
    token = getCurrentToken()
    params = event.info['params']
    tokenModel = Token()
    parentType = params.get('parentType')
    parentId = params.get('parentId', '')
    requiredScopes = {TOKEN_SCOPE_AUTHORIZED_UPLOAD, 'authorized_upload_folder_%s' % parentId}

    if parentType == 'folder' and tokenModel.hasScope(token=token, scope=requiredScopes):
        user = User().load(token['userId'], force=True)
        setCurrentUser(user)


def _storeUploadId(event):
    """
    Called after an upload is first initialized successfully. Sets the authorized upload ID
    in the token, ensuring it can be used for only this upload.
    """
    returnVal = event.info['returnVal']
    token = getCurrentToken()
    tokenModel = Token()
    isAuthorizedUpload = tokenModel.hasScope(token, TOKEN_SCOPE_AUTHORIZED_UPLOAD)

    if isAuthorizedUpload and returnVal.get('_modelType', 'upload') == 'upload':
        params = event.info['params']
        token['scope'].remove(TOKEN_SCOPE_AUTHORIZED_UPLOAD)
        token['authorizedUploadId'] = returnVal['_id']
        token['authorizedUploadDescription'] = params.get('authorizedUploadDescription', '')
        token['authorizedUploadEmail'] = params.get('authorizedUploadEmail')
        tokenModel.save(token)


@access.public
def _authorizeUploadStep(event):
    """
    Called before any requests dealing with partially completed uploads. Sets the
    request thread user to the authorized upload token creator if the requested
    upload is an authorized upload.
    """
    token = getCurrentToken()
    try:
        uploadId = ObjectId(event.info['params'].get('uploadId', ''))
    except InvalidId:
        # Take no action, 'uploadId' will be validated again by the endpoint
        return

    if token and 'authorizedUploadId' in token and token['authorizedUploadId'] == uploadId:
        user = User().load(token['userId'], force=True)
        setCurrentUser(user)


def _uploadComplete(event):
    """
    Called after an upload finishes. We check if our current token is a special
    authorized upload token, and if so, delete it.

    TODO we could alternatively keep a reference count inside each token that authorized
    more than a single upload at a time, and just decrement it here.
    """
    token = getCurrentToken()
    if token and 'authorizedUploadId' in token:
        user = User().load(token['userId'], force=True)
        item = Item().load(event.info['file']['itemId'], force=True)

        # Save the metadata on the item
        item['description'] = token['authorizedUploadDescription']
        item['authorizedUploadEmail'] = token['authorizedUploadEmail']
        Item().save(item)

        text = mail_utils.renderTemplate('authorized_upload.uploadFinished.mako', {
            'itemId': item['_id'],
            'itemName': item['name'],
            'itemDescription': item.get('description', '')
        })
        mail_utils.sendMail('Authorized upload complete', text, [user['email']])
        Token().remove(token)


class AuthorizedUploadPlugin(GirderPlugin):
    DISPLAY_NAME = 'Authorized Uploads'

    def load(self, info):
        name = 'authorized_upload'

        mail_utils.addTemplateDirectory(os.path.join(_HERE, 'mail_templates'))

        events.bind('rest.post.file.before', name, _authorizeInitUpload)
        events.bind('rest.post.file.after', name, _storeUploadId)
        events.bind('rest.post.file/chunk.before', name, _authorizeUploadStep)
        events.bind('rest.post.file/completion.before', name, _authorizeUploadStep)
        events.bind('rest.get.file/offset.before', name, _authorizeUploadStep)
        events.bind('model.file.finalizeUpload.after', name, _uploadComplete)

        info['apiRoot'].authorized_upload = AuthorizedUpload()

        registerPluginStaticContent(
            plugin='authorized_upload',
            css=['/style.css'],
            js=['/girder-plugin-authorized-upload.umd.cjs'],
            staticDir=Path(__file__).parent / 'web_client' / 'dist',
            tree=info['serverRoot'],
        )
