import FolderModel from '@girder/core/models/FolderModel';
import View from '@girder/core/views/View';
import UploadWidget from '@girder/core/views/widgets/UploadWidget';
import { setCurrentToken } from '@girder/core/auth';

import template from '../templates/authorizedUpload.pug';
import '../stylesheets/authorizedUpload.styl';

var AuthorizedUploadView = View.extend({
    initialize: function (settings) {
        // Fake a parent folder model (we might not have read access to fetch it)
        this.folder = new FolderModel({
            _id: settings.folderId,
            name: ''
        });
        setCurrentToken(settings.token);

        this.uploadWidget = new UploadWidget({
            parent: this.folder,
            title: false,
            multiFile: false,
            modal: false,
            parentView: this,
            otherParams: () => {
                return {
                    authorizedUploadDescription: this.$('#g-authorized-upload-description').val(),
                    authorizedUploadEmail: this.$('#g-authorized-upload-email').val()
                };
            }
        }).on('g:uploadFinished', function () {
            this.$('.g-upload-wrapper').addClass('hide');
            this.$('.g-complete-wrapper').removeClass('hide');
        }, this);
        this.render();
    },

    render: function () {
        this.$el.html(template());
        this.uploadWidget.setElement(this.$('.g-upload-widget-container')).render();
        return this;
    }
});

export default AuthorizedUploadView;
