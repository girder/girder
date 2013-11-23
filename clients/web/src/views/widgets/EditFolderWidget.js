/**
 * This widget is used to create a new folder or edit an existing one.
 */
girder.views.EditFolderWidget = Backbone.View.extend({
    events: {
        'submit #g-folder-edit-form': function () {
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

            return false;
        }
    },

    initialize: function (settings) {
        this.folder = settings.folder || null;
        this.parentType = settings.parentType;
        this.parentModel = settings.parentModel;
    },

    render: function () {
        var view = this;
        this.$el.html(jade.templates.editFolderWidget())
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-name').focus();
            });
        this.$('#g-name').focus();

        return this;
    },

    createFolder: function (fields) {
        girder.restRequest({
            path: 'folder',
            type: 'POST',
            data: _.extend(fields, {
                parentType: this.parentType,
                parentId: this.parentModel.get('_id')
            }),
            error: null // don't do default error behavior
        }).done(_.bind(function (resp) {
            this.$el.modal('hide');
            this.trigger('g:saved', resp);
        }, this)).error(_.bind(function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-folder').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this));
    },

    updateFolder: function (fields) {
        girder.restRequest({
            path: 'folder/' + this.folder.get('_id'),
            type: 'PUT',
            data: fields,
            error: null // don't do default error behavior
        }).done(_.bind(function (resp) {
            this.$el.modal('hide');
            this.trigger('g:saved', resp);
        }, this)).error(_.bind(function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-folder').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this));


    }
});
