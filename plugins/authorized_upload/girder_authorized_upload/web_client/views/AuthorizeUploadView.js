import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';

import template from '../templates/authorizeUpload.pug';
import '../stylesheets/authorizeUpload.styl';

var AuthorizeUploadView = View.extend({
    events: {
        'click .g-create-authorized-upload': function () {
            restRequest({
                url: 'authorized_upload',
                method: 'POST',
                data: {
                    folderId: this.folder.id,
                    duration: this.$('.g-num-days').val() || 30
                }
            }).done((data) => {
                this.$('.g-url-container').removeClass('hide');
                this.$('.g-authorized-upload-url-target').val(data.url).select();
            });
        }
    },

    initialize: function (settings) {
        this.folder = settings.folder;
        this.render();
    },

    render: function () {
        this.$el.html(template({
            folder: this.folder
        }));
        return this;
    }
});

export default AuthorizeUploadView;
