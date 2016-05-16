var DialogHelper = require('girder/utilities/DialogHelper');
var View         = require('girder/view');

var EditFileWidgetTemplate = require('girder/templates/widgets/editFileWidget.jade');

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
                this.$('button.g-save-file').removeClass('disabled');
                this.$('#g-' + err.responseJSON.field).focus();
            }, this).save();

            this.$('button.g-save-file').addClass('disabled');
            this.$('.g-validation-failed-message').empty();

            return false;
        }
    },

    initialize: function (settings) {
        this.file = settings.file || null;
    },

    render: function () {
        var view = this;
        if (this.file.get('mimeType') === undefined) {
            this.file.set('mimeType', '');
        }
        this.$el.html(EditFileWidgetTemplate({file: this.file}))
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-name').select().focus();
            }).on('hidden.bs.modal', function () {
                DialogHelper.handleClose('fileedit', undefined,
                                           view.file.get('_id'));
            });
        DialogHelper.handleOpen('fileedit', undefined, this.file.get('_id'));
        return this;
    }
});

module.exports = EditFileWidget;
