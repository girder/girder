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
    },

    render: function () {
        var showItems = false,
            input = false,
            preview = true,
            type = this.model.get('type'),
            validate = this._validateSelection,
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
        if (type === 'new-folder') {
            title = 'Create a new folder';
            help = 'Browse to a path, enter a name, then click "Save"';
            input = {
                label: 'Name',
                placeholder: 'Choose a name for the new folder',
                validate: (val) => {
                    // validation on the "new item name"
                    if (!val) {
                        return 'Please provide a folder name.';
                    }
                },
                default: this.model.get('fileName')
            };
            // validation on the parent model
            validate = (model) => {
                var type = model.get('_modelType');
                if (!_.contains(['folder', 'collection', 'user'], type)) {
                    return 'Invalid parent type, please choose a collection, folder, or user.';
                }
            };
            preview = false;
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
            validate: _.bind(validate, this)
        });
        this._browserWidget.once('g:saved', (model, inputValue) => {
            this._browserWidget.$el.modal('hide');
            if (type === 'file') {
                this._file.once('g:fetched', () => {
                    this.model.set({
                        value: this._file,
                        fileName: inputValue || this._file.name()
                    });
                    this.trigger('g:saved');
                }).fetch();
            }
            else {
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

    _validateSelection: function (item) {
        switch (this.model.get('type')) {
            case 'file':
                return restRequest({path: '/item/' + item.id + '/files', data: {limit: 1}})
                    .then((resp) => {
                        if (resp.length !== 1) {
                            throw 'Please select an item with exactly one file.';
                        }
                        this._file = new FileModel({_id: resp[0]._id});
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
    },
});

export default ItemSelectorWidget;
