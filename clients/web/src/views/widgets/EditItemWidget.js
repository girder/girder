import $ from 'jquery';
import _ from 'underscore';

import ItemModel from 'girder/models/ItemModel';
import View from 'girder/views/View';
import { handleClose, handleOpen } from 'girder/dialog';

import EditItemWidgetTemplate from 'girder/templates/widgets/editItemWidget.pug';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

/**
 * This widget is used to create a new item or edit an existing one.
 */
var EditItemWidget = View.extend({
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

            this.$('button.g-save-item').girderEnable(false);
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
        var modal = this.$el.html(EditItemWidgetTemplate({
            item: this.item}))
            .girderModal(this).on('shown.bs.modal', function () {
                view.$('#g-name').focus();
                if (view.item) {
                    handleOpen('itemedit');
                } else {
                    handleOpen('itemcreate');
                }
            }).on('hidden.bs.modal', function () {
                if (view.create) {
                    handleClose('itemcreate');
                } else {
                    handleClose('itemedit');
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
        var item = new ItemModel();
        item.set(_.extend(fields, {
            folderId: this.parentModel.get('_id')
        }));
        item.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', item);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-item').girderEnable(true);
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
            this.$('button.g-save-item').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    }
});

export default EditItemWidget;
