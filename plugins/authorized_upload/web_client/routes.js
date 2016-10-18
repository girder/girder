import router from 'girder/router';
import events from 'girder/events';
import FolderModel from 'girder/models/FolderModel';
import { Layout } from 'girder/constants';

import AuthorizeUploadView from './views/AuthorizeUploadView';
import AuthorizedUploadView from './views/AuthorizedUploadView';

router.route('authorize_upload/:folderId', 'authorizeUpload', (folderId) => {
    var folder = new FolderModel({_id: folderId}).once('g:fetched', () => {
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
