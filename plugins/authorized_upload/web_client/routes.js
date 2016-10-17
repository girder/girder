import router from 'girder/router';
import events from 'girder/events';
import FolderModel from 'girder/models/FolderModel';

import AuthorizeUploadView from './views/AuthorizeUploadView';

router.route('authorize_upload/:folderId', 'authorizeUpload', (folderId) => {
    var folder = new FolderModel({_id: folderId}).once('g:fetched', () => {
        events.trigger('g:navigateTo', AuthorizeUploadView, {
            folder: folder
        });
    });
    folder.fetch();
});

router.route('authorized_upload/:token/:folderId', 'authorizedUpload', function (token, folderId) {
    // TODO
});
