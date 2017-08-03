import _ from 'underscore';

import { getCurrentUser } from 'girder/auth';
import BrowserWidget from 'girder/views/widgets/BrowserWidget';
import View from 'girder/views/View';
import ItemModel from 'girder/models/ItemModel';
import { restRequest } from 'girder/rest';

var ItemSelectorWidget = View.extend({
    events: {
        'submit .g-new-file-select-form': '_selectButton'
    },

    initialize: function (settings) {
        if (!this.model) {
            this.model = new ItemModel();
        }
    },

    render: function () {
        var showItems = false,
            input = false,
            preview = true,
            type = this.model.get('type'),
            title, help;

        // Customize the browser widget according the argument type
        if (type === 'item' || type === 'file' || type === 'image') {
            showItems = true;
            title = 'Select an item';
            help = 'Click on an item to select it, then click "Save"';
        }

        if (type === 'directory') {
            title = 'Select a folder';
            help = 'Browse to a directory to select it, then click "Save"';
        }

        if (type === 'new-file') {
            title = 'Create a new item';
            help = 'Browse to a path, enter a name, then click "Save"';
            input = {
                label: 'Name',
                placeholder: 'Choose a name for the new item',
                default: this.model.get('fileName')
            };
            preview = false;
        }

        this._browserWidget = new BrowserWidget({
            el: $('#g-dialog-container'),
            parentView: this,
            showItems: showItems,
            selectItem: showItems,
            root: getCurrentUser(),
            titleText: title,
            helpText: help,
            input: input,
            showPreview: preview,
            validate: _.bind(this._validateSelection, this)
        }).render();
        this._browserWidget.once('g:saved', (model, inputValue) => {
            this._browserWidget.$el.modal('hide');
            this.model.set({
                value: model,
                fileName: inputValue || model.name()
            });
            this.trigger('g:saved');
        });

        return this;
    },

    _validateSelection: function (item) {
        switch (this.model.get('type')) {
            case 'file':
                return restRequest({path: '/item/' + item.id + '/files', data: {limit: 1}})
                    .then((resp) => {
                        if (!resp.length) {
                            console.log('file');
                            throw 'Please select an item with at least one file.';
                        }
                        return undefined;
                    }, () => {
                        throw 'There was an error listing files for the selected item.';
                    });
                break;
            case 'image':
                var image = item.get('largeImage');
                var isImage = $.Deferred()
                if (!image) {
                    isImage.reject('Please select a "large_image" item.');
                } else {
                    isImage.resolve();
                }
                return isImage.promise();
            default:
                return $.Deferred().resolve().promise();
        }
    },

    _selectButton: function (e) {
        e.preventDefault();

        var inputEl = this.$('#s-new-file-name');
        var inputElGroup =  inputEl.parent();
        var fileName = inputEl.val();
        var type = this.model.get('type');
        var parent = this._hierarchyView.parentModel;
        var errorEl = this.$('.s-modal-error').addClass('hidden');

        inputElGroup.removeClass('has-error');

        switch (type) {
            case 'new-file':
                // a file name must be provided
                if (!fileName) {
                    inputElGroup.addClass('has-error');
                    errorEl.removeClass('hidden')
                        .text('You must provide a name for the new file.');
                    return;
                }
                // the parent must be a folder
                if (parent.resourceName !== 'folder') {
                    errorEl.removeClass('hidden')
                        .text('Files cannot be added under collections.');
                    return;
                }
                this.model.set({
                    parent: parent,
                    value: new ItemModel({
                        name: fileName,
                        folderId: parent.id
                    })
                });
                break;
            case 'directory':
                this.model.set({
                    value: parent
                });
                break;
        }
        this.trigger('g:saved');
        this.$el.modal('hide');
    }
});

export default ItemSelectorWidget;
