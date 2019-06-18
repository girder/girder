import View from '@girder/core/views/View';
import { handleClose, handleOpen } from '@girder/core/dialog';

import EditFileWidgetTemplate from '@girder/core/templates/widgets/editFileWidget.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This widget is used to edit file information.
 */
var EditFileWidget = View.extend({
    events: {
        'submit #g-file-edit-form': function () {
            var fields = {
                name: this.$('#g-name').val(),
                mimeType: this.$('#g-mimetype').val()
            };

            this.file.set(fields);
            this.file.off(null, null, this).on('g:saved', function () {
                this.$el.modal('hide');
                this.trigger('g:saved', this.file);
            }, this).on('g:error', function (err) {
                this.$('.g-validation-failed-message').text(err.responseJSON.message);
                this.$('button.g-save-file').girderEnable(true);
                this.$('#g-' + err.responseJSON.field).focus();
            }, this).save();

            this.$('button.g-save-file').girderEnable(false);
            this.$('.g-validation-failed-message').empty();

            return false;
        }
    },

    initialize: function (settings) {
        this.file = settings.file || null;
    },

    render: function () {
        if (this.file.get('mimeType') === undefined) {
            this.file.set('mimeType', '');
        }
        this.$el.html(EditFileWidgetTemplate({file: this.file}))
            .girderModal(this).on('shown.bs.modal', () => {
                this.$('#g-name').select().focus();
            }).on('hidden.bs.modal', () => {
                handleClose('fileedit', undefined, this.file.get('_id'));
            });
        handleOpen('fileedit', undefined, this.file.get('_id'));
        return this;
    }
});

export default EditFileWidget;
