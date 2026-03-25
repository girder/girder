import $ from 'jquery';
import _ from 'underscore';

import ItemModel from '@girder/core/models/ItemModel';
import MarkdownWidget from '@girder/core/views/widgets/MarkdownWidget';
import View from '@girder/core/views/View';
import { handleClose, handleOpen } from '@girder/core/dialog';

import EditItemWidgetTemplate from '@girder/core/templates/widgets/editItemWidget.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/utilities/jquery/girderModal';

/**
 * This widget is used to create a new item or edit an existing one.
 */
var EditItemWidget = View.extend({
    events: {
        'submit #g-item-edit-form': function () {
            var fields = {
                name: this.$('#g-name').val(),
                description: this.descriptionEditor.val()
            };

            if (this.item) {
                this.updateItem(fields);
            } else {
                this.createItem(fields);
            }

            this.descriptionEditor.saveText();
            this.$('button.g-save-item').girderEnable(false);
            this.$('.g-validation-failed-message').empty();

            return false;
        }
    },

    initialize: function (settings) {
        this.item = settings.item || null;
        this.parentModel = settings.parentModel;
        this.descriptionEditor = new MarkdownWidget({
            text: this.item ? this.item.get('description') : '',
            prefix: 'item-description',
            placeholder: 'Enter a description',
            enableUploads: false,
            parentView: this
        });
    },

    render: function () {
        var modal = this.$el.html(EditItemWidgetTemplate({
            item: this.item
        })).girderModal(this).on('shown.bs.modal', () => {
            this.$('#g-name').trigger('focus');
            if (this.item) {
                handleOpen('itemedit');
            } else {
                handleOpen('itemcreate');
            }
        }).on('hidden.bs.modal', () => {
            if (this.create) {
                handleClose('itemcreate');
            } else {
                handleClose('itemedit');
            }
        }).on('ready.girder.modal', () => {
            if (this.item) {
                this.$('#g-name').val(this.item.get('name'));
                this.$('#g-description').val(this.item.get('description'));
                this.create = false;
            } else {
                this.create = true;
            }
        });
        modal.trigger($.Event('ready.girder.modal', { relatedTarget: modal }));
        this.descriptionEditor.setElement(this.$('.g-description-editor-container')).render();

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
            this.$('#g-' + err.responseJSON.field).trigger('focus');
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
            this.$('#g-' + err.responseJSON.field).trigger('focus');
        }, this).save();
    }
});

export default EditItemWidget;
