import _ from 'underscore';

import { getCurrentUser } from 'girder/auth';
import BrowserWidget from 'girder/views/widgets/BrowserWidget';
import View from 'girder/views/View';
import ItemModel from 'girder/models/ItemModel';
import FileModel from 'girder/models/FileModel';
import { restRequest } from 'girder/rest';

var ItemSelectorWidget = View.extend({

    initialize: function (settings) {
        if (!this.model) {
            this.model = new ItemModel();
        }
        this.root = settings.root || getCurrentUser();
    },

    render: function () {
        var showItems = false,
            input = false,
            preview = true,
            type = this.model.get('type'),
            validate = _.bind(this._validateInputSelection, this),
            title, help;

        var validationPromise = function (condition, message) {
            var isValid = $.Deferred();
            if (!condition) {
                isValid.reject(message);
            } else {
                isValid.resolve();
            }
            return isValid.promise();
        };
        // Customize the browser widget according the argument type
        if (type === 'file' || type === 'image') {
            showItems = true;
            title = 'Select an item';
            help = 'Click on an item to select it, then click "Save"';
        } else if (type === 'directory') {
            title = 'Select a folder';
            help = 'Browse to a directory to select it, then click "Save"';
        } else if (type === 'new-folder') {
            title = 'Create a new folder';
            help = 'Browse to a path, enter a name, then click "Save"';
            input = {
                label: 'Name',
                placeholder: 'Choose a name for the new folder',
                validate: (val) => {
                    // validation on the "new folder name"
                    return validationPromise(val, 'Please provide a folder name.');
                },
                default: this.model.get('fileName')
            };
            // validation on the parent model
            validate = (model) => {
                var type = model.get('_modelType');
                return validationPromise(_.contains(['folder', 'collection', 'user'], type),
                    'Invalid parent type, please choose a collection, folder, or user.');
            };
            preview = false;
        } else if (type === 'new-file') {
            title = 'Create a new item';
            help = 'Browse to a path, enter a name, then click "Save"';
            input = {
                label: 'Name',
                placeholder: 'Choose a name for the new item',
                validate: (val) => {
                    // validation on the "new item name"
                    return validationPromise(val, 'Please provide an item name.');
                },
                default: this.model.get('fileName')
            };
            // validation on the parent model
            validate = (model) => {
                var type = model.get('_modelType');
                return validationPromise(type === 'folder', 'Invalid parent type, please choose a folder.');
            };
            preview = false;
        }
        this._browserWidget = new BrowserWidget({
            el: $('#g-dialog-container'),
            parentView: this,
            showItems: showItems,
            selectItem: showItems,
            root: this.root,
            titleText: title,
            helpText: help,
            input: input,
            showPreview: preview,
            validate: validate
        });
        this._browserWidget.once('g:saved', (model, inputValue) => {
            this.root = this._browserWidget.root;
            this._browserWidget.$el.modal('hide');
            if (type === 'file') {
                this.model.set({
                    value: this._file,
                    fileName: inputValue || this._file.name()
                });
                this.trigger('g:saved');
            } else {
                this.model.set({
                    value: model,
                    fileName: inputValue || model.name()
                });
                this.trigger('g:saved');
            }
        });
        this._browserWidget.render();
        return this;
    },

    _validateInputSelection: function (item) {
        // NOTE: As a side-effect to validating a file, if the file is valid it is fetched to be
        // saved as the selected model once the BrowserWidget's g:saved event fires.
        if (!item) {
            return $.Deferred().reject('No item selected.').promise();
        }
        switch (this.model.get('type')) {
            case 'file':
                return restRequest({
                    url: '/item/' + item.id + '/files',
                    data: {
                        limit: 2
                    }
                })
                .then((resp) => {
                    if (resp.length !== 1) {
                        throw 'Please select an item with exactly one file.';
                    }
                    this._file = new FileModel(resp[0]);
                    return undefined;
                }, () => {
                    throw 'There was an error listing files for the selected item.';
                });
            case 'image':
                var image = item.get('largeImage');
                var isImage = $.Deferred();
                if (!image) {
                    isImage.reject('Please select a "large_image" item.');
                } else {
                    isImage.resolve();
                }
                return isImage.promise();
            default:
                return $.Deferred().resolve().promise();
        }
    }
});

export default ItemSelectorWidget;
