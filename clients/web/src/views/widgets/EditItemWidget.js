/**
 * This widget is used to create a new item or edit an existing one.
 */
girder.views.EditItemWidget = girder.View.extend({
    events: {
        'submit #g-item-edit-form': function () {
            var fields = {
                name: this.$('#g-name').val(),
                description: this.$('#g-description').val()
            };

            if (this.item) {
                this.updateItem(fields);
            } else {
                this.createItem(fields);
            }

            this.$('button.g-save-item').addClass('disabled');
            this.$('.g-validation-failed-message').empty();

            return false;
        }
    },

    initialize: function (settings) {
        this.item = settings.item || null;
        this.parentModel = settings.parentModel;
    },

    render: function () {
        var view = this;
        var modal = this.$el.html(girder.templates.editItemWidget({
            item: this.item}))
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-name').focus();
                if (view.item) {
                    girder.dialogs.handleOpen('itemedit');
                } else {
                    girder.dialogs.handleOpen('itemcreate');
                }
            }).on('hidden.bs.modal', function () {
                if (view.create) {
                    girder.dialogs.handleClose('itemcreate');
                } else {
                    girder.dialogs.handleClose('itemedit');
                }
            }).on('ready.girder.modal', function () {
                if (view.item) {
                    view.$('#g-name').val(view.item.get('name'));
                    view.$('#g-description').val(view.item.get('description'));
                    view.create = false;
                } else {
                    view.create = true;
                }
            });
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));

        return this;
    },

    createItem: function (fields) {
        var item = new girder.models.ItemModel();
        item.set(_.extend(fields, {
            folderId: this.parentModel.get('_id')
        }));
        item.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', item);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-item').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    },

    updateItem: function (fields) {
        this.item.set(fields);
        this.item.off().on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', this.item);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-item').removeClass('disabled');
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    }
});
