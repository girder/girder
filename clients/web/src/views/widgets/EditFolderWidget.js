/**
 * This widget is used to create a new folder or edit an existing one.
 */
girder.views.EditFolderWidget = girder.View.extend({
    events: {
        'submit #g-folder-edit-form': function (e) {
            e.preventDefault();
            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val()
            };

            if (this.folder) {
                this.updateFolder(fields);
            }
            else {
                this.createFolder(fields);
            }

            this.$('button.g-save-folder').addClass('disabled');
            this.$('.g-validation-failed-message').text('');
        }
    },

    initialize: function (settings) {
        this.folder = settings.folder || null;
        this.parentModel = settings.parentModel;
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.editFolderWidget({
            folder: this.folder
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-name').focus();
            if (view.folder) {
                view.$('#g-name').val(view.folder.get('name'));
                view.$('#g-description').val(view.folder.get('description'));
            }
            girder.dialogs.handleOpen('folderedit');
        }).on('hidden.bs.modal', function () {
            girder.dialogs.handleClose('folderedit');
        });
        this.$('#g-name').focus();

        return this;
    },

    createFolder: function (fields) {
        var folder = new girder.models.FolderModel();
        folder.set(_.extend(fields, {
            parentType: this.parentModel.resourceName,
            parentId: this.parentModel.get('_id')
        }));
        folder.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', folder);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-folder').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },

    updateFolder: function (fields) {
        this.folder.set(fields);
        this.folder.off().on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.folder);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-folder').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    }
});
