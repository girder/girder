import $ from 'jquery';
import _ from 'underscore';

import FolderModel from 'girder/models/FolderModel';
import MarkdownWidget from 'girder/views/widgets/MarkdownWidget';
import View from 'girder/views/View';
import { handleClose, handleOpen } from 'girder/dialog';

import EditFolderWidgetTemplate from 'girder/templates/widgets/editFolderWidget.pug';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

/**
 * This widget is used to create a new folder or edit an existing one.
 */
var EditFolderWidget = View.extend({
    events: {
        'submit #g-folder-edit-form': function (e) {
            e.preventDefault();
            var fields = {
                name: this.$('#g-name').val(),
                description: this.descriptionEditor.val()
            };

            if (this.folder) {
                this.updateFolder(fields);
            } else {
                this.createFolder(fields);
            }

            this.descriptionEditor.saveText();
            this.$('button.g-save-folder').girderEnable(false);
            this.$('.g-validation-failed-message').text('');
        }
    },

    initialize: function (settings) {
        this.folder = settings.folder || null;
        this.parentModel = settings.parentModel;
        this.descriptionEditor = new MarkdownWidget({
            text: this.folder ? this.folder.get('description') : '',
            prefix: 'folder-description',
            placeholder: 'Enter a description',
            parent: this.folder,
            allowedExtensions: ['png', 'jpg', 'jpeg', 'gif'],
            enableUploads: !!this.folder,
            parentView: this
        }).on('g:fileUploaded', function (args) {
            this.trigger('g:fileUploaded', args);
        }, this);
    },

    render: function () {
        var view = this;
        var modal = this.$el.html(EditFolderWidgetTemplate({
            folder: this.folder
        })).girderModal(this).on('shown.bs.modal', function () {
            view.$('#g-name').focus();
            if (view.folder) {
                handleOpen('folderedit');
            } else {
                handleOpen('foldercreate');
            }
        }).on('hidden.bs.modal', function () {
            if (view.create) {
                handleClose('foldercreate');
            } else {
                handleClose('folderedit');
            }
        }).on('ready.girder.modal', function () {
            if (view.folder) {
                view.$('#g-name').val(view.folder.get('name'));
                view.descriptionEditor.val(view.folder.get('description'));
                view.create = false;
            } else {
                view.create = true;
            }
        });
        modal.trigger($.Event('ready.girder.modal', {relatedTarget: modal}));
        this.$('#g-name').focus();
        this.descriptionEditor.setElement(
            this.$('.g-description-editor-container')).render();

        return this;
    },

    createFolder: function (fields) {
        var folder = new FolderModel();
        folder.set(_.extend(fields, {
            parentType: this.parentModel.resourceName,
            parentId: this.parentModel.get('_id')
        }));
        folder.on('g:saved', function () {
            this.$el.modal('hide');
            this.trigger('g:saved', folder);
        }, this).on('g:error', function (err) {
            this.$('.g-validation-failed-message').text(err.responseJSON.message);
            this.$('button.g-save-folder').girderEnable(true);
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
            this.$('button.g-save-folder').girderEnable(true);
            this.$('#g-' + err.responseJSON.field).focus();
        }, this).save();
    }
});

export default EditFolderWidget;
