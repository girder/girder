from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import loadmodel, Resource
from girder.constants import AccessType, TokenScope
from girder.exceptions import ValidationException
from girder.models.setting import Setting
from girder.models.token import Token
from girder.settings import SettingKey
from girder.utility import mail_utils

from .constants import TOKEN_SCOPE_AUTHORIZED_UPLOAD


class AuthorizedUpload(Resource):
    def __init__(self):
        super().__init__()
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
