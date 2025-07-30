const $ = girder.$;
const _ = girder._;
const BrowserWidget = girder.views.widgets.BrowserWidget;
const FileModel = girder.models.FileModel;
const ItemModel = girder.models.ItemModel;
const { restRequest } = girder.rest;
const { getCurrentUser } = girder.auth;

const ItemSelectorWidget = BrowserWidget.extend({
    initialize(settings) {
        if (!this.model) {
            this.model = new ItemModel();
        }
        const t = this.model.get('type');
        settings.showItems = true;
        settings.submitText = 'Confirm';

        settings.validate = (model) => this._validateModel(model);
        if (!settings.defaultSelectedResource && !(settings.rootSelectorSettings && settings.rootSelectorSettings.selectByResource)) {
            settings.root = settings.rootPath || getCurrentUser();
        }
        if (settings.root === false && !settings.defaultSelectedResource) {
            settings.root = null;
        }

        settings.paginated = true;

        switch (t) {
            case 'directory':
                settings.titleText = 'Select a directory';
                break;
            case 'file':
                settings.titleText = 'Select a file';
                settings.selectItem = true;
                settings.showPreview = false;
                break;
            case 'image':
                settings.titleText = 'Select an image';
                settings.selectItem = true;
                settings.showPreview = false;
                break;
            case 'item':
                settings.titleText = 'Select an item';
                settings.selectItem = true;
                settings.showPreview = false;
                break;
            case 'multi':
                settings.titleText = 'Select files';
                settings.selectItem = false;
                settings.highlightItem = false;
                settings.input = {
                    label: 'Item Filter (Regular Expression)',
                    validate: (val) => {
                        try {
                            const regExp = RegExp(val);
                            if (regExp) {
                                return $.Deferred().resolve().promise();
                            }
                        } catch (exception) {
                            return $.Deferred().reject('Specify a valid Regular Expression').promise();
                        }
                    }
                };
                settings.showPreview = false;
                break;
            case 'new-file':
                settings.titleText = 'Select a directory';
                settings.input = {
                    label: 'Item name',
                    validate: (val) => {
                        if ((val && val.trim()) || (!val && !this.model.required)) {
                            return $.Deferred().resolve().promise();
                        }
                        return $.Deferred().reject('Specify an item name').promise();
                    }
                };
                settings.showPreview = false;
                break;
        }
        settings.titleText += ` for "${this.model.get('title')}"`;

        this.on('g:saved', (model, fileName) => this._saveModel(model, fileName));

        return BrowserWidget.prototype.initialize.apply(this, arguments);
    },
    render() {
        BrowserWidget.prototype.render.apply(this, arguments);

        const t = this.model.get('type');
        if (['file', 'image', 'item'].includes(t)) {
            this.$('.modal-footer').hide();
        }
        if (t === 'multi') {
            this.$('#g-input-element').attr('placeholder', '(all)');
            this.$('.g-item-list-entry').addClass('g-selected');

            this.$('#g-input-element').on('input', () => this.processRegularExpression());
            if (this.model.get('value') && this.model.get('value').get('name')) {
                this.$('#g-input-element').val(this.model.get('value').get('name'));
            }
        }
        return this;
    },

    /**
     * While type is multi this will check the input element for a regular expression.
     * Will apply highlighting to existing items if a valid expression
     * If not valid it will provide feedback to the user that it is invalid
     */
    processRegularExpression() {
        const reg = this.$('#g-input-element').val();
        this.$('.g-item-list-entry').removeClass('g-selected');
        try {
            const regEx = new RegExp(reg, 'g');
            this.$('.g-validation-failed-message').addClass('hidden');
            this.$('.g-input-element.form-group').removeClass('has-error');

            this.$('.g-item-list-entry').each((index, item) => {
                if (this.$(item)) {
                    item = this.$(item);
                    const link = item.find('.g-item-list-link[href]').filter((idx, l) => $(l).find('i.icon-doc-text-inv').length);
                    const text = link.text();
                    if (text.match(regEx) || reg === '') {
                        this.$(item).addClass('g-selected');
                    }
                }
            });
        } catch (exception) {
            if (exception instanceof SyntaxError) {
                this.$('.g-validation-failed-message').text('Specify a valid Regular Expression');
                this.$('.g-validation-failed-message').removeClass('hidden');
                this.$('.g-input-element.form-group').addClass('has-error');
            }
        }
    },
    /**
     * Get the currently displayed path in the hierarchy view.
     */
    _path() {
        let path = this._hierarchyView.breadcrumbs.map((d) => d.get('name'));

        if (this.model.get('type') === 'directory') {
            path = _.initial(path);
        }
        return path;
    },
    /**
     * Checks when the model changes and binds to the changed of itemListView to select items in multi mode
     */
    _selectModel() {
        BrowserWidget.prototype._selectModel.apply(this, arguments);
        if (this.model.get('type') === 'multi' && this._hierarchyView) {
            // If changing the model process the regular expression
            if (this._hierarchyView.itemListView) {
                this._hierarchyView.itemListView.once('g:changed', (evt) => {
                    this.processRegularExpression();
                });
            } else {
                // When initialized the itemListView doesn't exist to process the regularExpression
                // wait until items are added to highlight based on regularExpression
                this.checkItemsLoaded(100);
            }
        }
    },
    /**
     * Best tool I could come up with to highlight regular expressions on load.  Waits for the entries to display
     * and then computes the regular expression if one exists.
     * @param {number} timeout
     */
    checkItemsLoaded(timeout) {
        if (this.$('.g-folder-list').length || this.$('.g-item-list').length) {
            clearTimeout(this.checkItemsTimeout);
            this.processRegularExpression();
        } else {
            this.checkItemsTimeout = setTimeout(() => this.checkItemsLoaded(timeout), timeout);
        }
    },
    _validateModel(model) {
        const t = this.model.get('type');
        let error;

        switch (t) {
            case 'directory':
            case 'new-file':
                if (!model || model.get('_modelType') !== 'folder') {
                    error = 'Select a directory.';
                }
                break;
            case 'file':
                if (!model) {
                    error = 'Select a file.';
                } else {
                    const result = $.Deferred();
                    restRequest({url: `/item/${model.id}/files`, data: {limit: 1}}).done((resp) => {
                        if (!resp.length) {
                            result.reject('Please select a item with at least one file.');
                        }
                        result.resolve(null);
                    }).fail(() => {
                        result.reject('There was an error listing files for the selected item.');
                    });
                    return result.promise();
                }
                break;
            case 'image':
                if (!model) {
                    error = 'Select an image.';
                } else if (!model.get('largeImage')) {
                    error = 'Please select a "large_image" item.';
                }
                break;
            case 'item':
                if (!model) {
                    error = 'Select an item.';
                }
                break;
        }
        if (error) {
            return $.Deferred().reject(error).promise();
        }
        return $.Deferred().resolve().promise();
    },

    _saveModel(model, fileName) {
        const t = this.model.get('type');
        switch (t) {
            case 'directory':
                this.model.set({
                    path: this._path(),
                    value: model
                });
                break;
            case 'file':
                restRequest({url: `/item/${model.id}/files`, data: {limit: 1}}).done((resp) => {
                    if (!resp.length) {
                        return;
                    }
                    const file = new FileModel({_id: resp[0]._id});
                    file.once('g:fetched', () => {
                        this.model.set({
                            path: this._path(),
                            value: file
                        });
                    }).fetch();
                });
                break;
            case 'image': {
                const image = model.get('largeImage');
                // Prefer the large_image fileId
                const file = new FileModel({ _id: image.fileId || image.originalId });
                file.once('g:fetched', () => {
                    this.model.set({
                        path: this._path(),
                        value: file
                    });
                }).fetch();
                break;
            }
            case 'item':
                this.model.set({
                    path: this._path(),
                    value: model
                });
                break;
            case 'new-file':
                if (!fileName) {
                    this.model.set({
                        path: this._path(),
                        parent: model,
                        value: null
                    });
                } else {
                    this.model.set({
                        path: this._path(),
                        parent: model,
                        value: new ItemModel({
                            name: fileName,
                            folderId: model.id
                        })
                    });
                }
                break;
            case 'multi':
                if (fileName.trim() === '') {
                    fileName = '.*';
                }
                this.model.set({
                    path: this._path(),
                    parent: model,
                    folderName: model.name(),
                    value: new ItemModel({
                        name: fileName,
                        folderId: model.id
                    })
                });
                break;
        }
    },

    _selectItem: function (item) {
        BrowserWidget.prototype._selectItem.apply(this, arguments);
        if (this.selectItem) {
            this.$('.g-submit-button').click();
        }
    }
});

export default ItemSelectorWidget;
