/* eslint-disable import/first */

const router = girder.router;
const events = girder.events;
const FolderModel = girder.models.FolderModel;
const Layout = girder.constants.Layout;

import AuthorizeUploadView from './views/AuthorizeUploadView';
import AuthorizedUploadView from './views/AuthorizedUploadView';

router.route('authorize_upload/:folderId', 'authorizeUpload', (folderId) => {
    var folder = new FolderModel({ _id: folderId }).once('g:fetched', () => {
        events.trigger('g:navigateTo', AuthorizeUploadView, {
            folder: folder
        });
    });
    folder.fetch();
});

router.route('authorized_upload/:folderId/:token', 'authorizedUpload', function (folderId, token) {
    events.trigger('g:navigateTo', AuthorizedUploadView, {
        token: token,
        folderId: folderId
    }, {
        layout: Layout.EMPTY
    });
});
