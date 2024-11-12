import ItemSelectorWidget from './ItemSelectorWidget';

import booleanWidget from '../templates/booleanWidget.pug';
import colorWidget from '../templates/colorWidget.pug';
import enumerationWidget from '../templates/enumerationWidget.pug';
import fileWidget from '../templates/fileWidget.pug';
import rangeWidget from '../templates/rangeWidget.pug';
import regionWidget from '../templates/regionWidget.pug';
import widget from '../templates/widget.pug';

import '../stylesheets/controlWidget.styl';
import 'bootstrap-colorpicker';
import 'bootstrap-colorpicker/dist/css/bootstrap-colorpicker.css';
import 'bootstrap-slider/dist/bootstrap-slider';
import 'bootstrap-slider/dist/css/bootstrap-slider.css';

const $ = girder.$;
const _ = girder._;
const moment = girder.moment;

const View = girder.views.View;
const { getCurrentUser } = girder.auth;
const events = girder.events;
const ItemModel = girder.models.ItemModel;
const FolderModel = girder.models.FolderModel;
const FolderCollection = girder.collections.FolderCollection;
const FileModel = girder.models.FileModel;
const UserModel = girder.models.UserModel;
const CollectionModel = girder.models.CollectionModel;
const { restRequest } = girder.rest;

const ControlWidget = View.extend({
    events: {
        'change input,select': '_input',
        changeColor: '_input',
        'click .s-select-file-button': '_selectFile',
        'click .s-select-multifile-button': '_selectMultiFile',
        'click .s-select-region-button': '_selectRegion',
        'click .s-select-region-clear-button': '_clearRegion',
        'click .s-select-region-submit-button': '_submitRegionToggle'
    },

    initialize(settings) {
        this._disableRegionSelect = settings.disableRegionSelect === true;
        this._rootPath = settings.rootPath;
        this.listenTo(this.model, 'change', this.change);
        this.listenTo(this.model, 'destroy', this.remove);
        this.listenTo(this.model, 'invalid', this.invalid);
        this.listenTo(events, 's:widgetSet:' + this.model.id, (value) => {
            this.model.set('value', value);
        });

        this._initModel(settings);
    },

    _initModel(settings) {
        const prefix = settings.setDefaultOutput;
        const model = this.model;
        const type = model.get('type');
        const channel = model.get('channel');
        const required = model.get('required');
        if (channel === 'input') {
            if (model.get('defaultNameMatch') || model.get('defaultPathMatch')) {
                this._getDefaultInputResource(model).then((resource) => {
                    if (!resource) {
                        return null;
                    }
                    this.model.set({
                        path: resource._path,
                        value: resource
                    });
                    return null;
                });
            }
        }
        if (!prefix || (!required && (!this._findReference() || !model.get('extensions'))) || channel !== 'output' || !['new-file', 'file', 'item', 'directory', 'multi'].includes(type)) {
            return;
        }
        this._getDefaultOutputFolder().then((folder) => {
            if (!folder) {
                return null;
            }
            const extension = (model.get('extensions') || '').split('|')[0];
            const modelName = model.get('id') === 'returnparameterfile' ? '' : `-${model.get('title')}`;
            const reference = this._findReference();
            if (reference) {
                this.listenTo(reference, 'change', () => {
                    const value = reference.get('value');
                    if (value && value.get('name')) {
                        let refName = value.get('name');
                        if (refName.includes('.')) {
                            refName = refName.slice(0, refName.lastIndexOf('.'));
                        }
                        const name = `${refName}-${prefix}${modelName}-${moment().local().format()}${extension}`;
                        this._setValue(folder, name);
                    }
                });
            } else {
                const name = `${prefix}${modelName}-${moment().local().format()}${extension}`;
                this._setValue(folder, name);
            }
            return null;
        });
    },

    _setValue(folder, name) {
        this.model.set({
            path: [folder.get('name'), name],
            parent: folder,
            value: new ItemModel({
                name,
                folderId: folder.id
            })
        });
    },

    _findReference() {
        const ref = this.model.get('reference');
        if (!ref) {
            return null;
        }
        // ref is an id of another model
        return this.model.collection.find((d) => d.get('id') === ref);
    },

    render(_, options) {
        this.$('[data-toggle="tooltip"]').tooltip('destroy');
        this.$('.form-group').removeClass('has-error');
        this.model.isValid();
        if (options && options.norender) {
            return this;
        }
        const params = Object.assign({
            disableRegionSelect: this._disableRegionSelect,
            previousElement: this.$el
        }, this.model.toJSON());
        this.$el.html(this.template()(params));
        this.$('[data-toggle="tooltip"]').tooltip({container: 'body'});
        if (params.datalist) {
            this.$('.s-control-item input').addClass('has-datalist');
        }
        return this;
    },

    change() {
        events.trigger(`s:widgetChanged:${this.model.get('type')}`, this.model);
        events.trigger('s:widgetChanged', this.model);
        this.render.apply(this, arguments);
    },

    remove() {
        events.trigger(`s:widgetRemoved:${this.model.get('type')}`, this.model);
        events.trigger('s:widgetRemoved', this.model);
        this.$('.s-control-item[data-type="color"] .input-group').colorpicker('destroy');
        this.$('.s-control-item[data-type="range"] input').slider('destroy');
        this.$el.empty();
    },

    /**
     * Set classes on the input element to indicate to the user that the current value
     * is invalid.  This is automatically triggered by the model's "invalid" event.
     */
    invalid() {
        events.trigger(`s:widgetInvalid:${this.model.get('type')}`, this.model);
        events.trigger('s:widgetInvalid', this.model);
        this.$('.form-group').addClass('has-error');
    },

    /**
     * Type definitions mapping used internally.  Each widget type
     * specifies it's pug template and possibly more customizations
     * as needed.
     */
    _typedef: {
        range: {
            template: rangeWidget
        },
        color: {
            template: colorWidget
        },
        string: {
            template: widget
        },
        number: {
            template: widget
        },
        integer: {
            template: widget
        },
        boolean: {
            template: booleanWidget
        },
        'string-vector': {
            template: widget
        },
        'number-vector': {
            template: widget
        },
        'string-enumeration': {
            template: enumerationWidget
        },
        'number-enumeration': {
            template: enumerationWidget
        },
        file: {
            template: fileWidget
        },
        item: {
            template: fileWidget
        },
        image: {
            template: fileWidget
        },
        multi: {
            template: fileWidget
        },
        directory: {
            template: fileWidget
        },
        'new-file': {
            template: fileWidget
        },
        region: {
            template: regionWidget
        }
    },

    /**
     * Get the appropriate template for the model type.
     */
    template() {
        const type = this.model.get('type');
        let def = this._typedef[type];

        if (def === undefined) {
            console.warn('Invalid widget type "' + type + '"'); // eslint-disable-line no-console
            def = {};
        }
        return def.template || _.template('');
    },

    /**
     * Get the current value from an input (or select) element.
     */
    _input(evt) {
        const $el = $(evt.target);
        let val = $el.val();

        if ($el.attr('type') === 'checkbox') {
            val = $el.get(0).checked;
        }

        // we don't want to rerender, because this event is generated by the input element
        this.model.set('value', val, {norender: true});
    },

    /**
     * Get the value from a file selection modal and set the text in the widget's
     * input element.
     */
    _selectFile() {
        // If we converted to multi, convert it back to the older type
        // We reset the name if it was multi before
        if (this.model.get('type') === 'multi') {
            if (this.model.get('value')) {
                this.model.set({
                    value: new ItemModel({
                        folderId: this.model.get('value').get('folderId')
                    })
                });
            }
        }
        const t = this.model.get('defaultType');

        if (t) {
            this.model.set({
                type: t
            });
        }

        const itemSelectorSettings = {
            el: $('#g-dialog-container'),
            parentView: this,
            model: this.model,
            rootPath: this._rootPath,
            rootSelectorSettings: {
                pageLimit: 1000
            }
        };
        if (this.model.get('value')) {
            this.getRoot(this.model.get('value'), itemSelectorSettings);
        } else {
            this.completeInitialization(itemSelectorSettings);
        }
    },
    /**
     * Used to collect the root of the resource passed to the itemSelectorWidget to enable the defaultSelectedResource
     * The value isn't always a valid model so we need to fetch the model from the itemId, folderID, or if it is the item, the actual item
     * @param {*} resource value object for model containing either itemId, folderId, or a standard model
     * @param {*} settings ItemSelectorWidget settings extended from BrowserWidget
     */
    getRoot(resource, settings) {
        const modelTypes = {
            item: ItemModel,
            folder: FolderModel,
            collection: CollectionModel,
            user: UserModel
        };
        let modelType = 'folder'; // folder type by default, other types if necessary
        let modelId = null;
        // If it is an item it will have a folderId associated with it as a parent item
        if (resource.get('itemId')) {
            modelId = resource.get('itemId');
            modelType = 'item';
        } else if (resource.get('folderId')) {
            modelId = resource.get('folderId');
        } else if (resource.get('parentCollection')) {
            // Case for providing a folder as the defaultSelectedResource but want the user to select an item
            // folder parent is either 'user' | 'folder' | 'collection', most likely folder though
            modelType = resource.get('parentCollection');
            modelId = resource.get('parentId');
        }
        // We need to fetch the itemID to get the model stuff
        if (modelType === 'item') {
            const itemModel = new modelTypes[modelType]();
            itemModel.set({
                _id: modelId
            }).on('g:fetched', function () {
                settings.defaultSelectedResource = itemModel;
                settings.highlightItem = true;
                settings.selectItem = true;
                this.getRoot(itemModel, settings);
            }, this).on('g:error', function () {
                settings.root = null;
                this.completeInitialization(settings);
            }, this).fetch();
        } else if (modelTypes[modelType] && modelId) {
            const parentModel = new modelTypes[modelType]();
            parentModel.set({
                _id: modelId
            }).on('g:fetched', function () {
                settings.root = parentModel;
                settings.rootSelectorSettings.selectByResource = parentModel;
                this.completeInitialization(settings);
            }, this).on('g:error', function () {
                settings.root = null;
                this.completeInitialization(settings);
            }, this).fetch();
        } else {
            this.completeInitialization(settings);
        }
    },
    completeInitialization(settings) {
        const modal = new ItemSelectorWidget(settings);
        modal.once('g:saved', () => {
            this.model.unset('revertType');
            modal.$el.modal('hide');
        }).render();
        modal.$el.on('hidden.bs.modal', () => {
            if (this.model.get('revertType')) {
                this.model.set('type', this.model.get('revertType'));
                this.model.unset('revertType');
            }
        });
    },
    _selectMultiFile() {
        // Store the current type in case it is opened again
        const t = this.model.get('type');
        if (t !== 'multi') {
            this.model.set({
                type: 'multi',
                defaultType: t,
                revertType: t
            });
        }

        const itemSelectorSettings = {
            el: $('#g-dialog-container'),
            parentView: this,
            model: this.model,
            rootPath: this._rootPath,
            rootSelectorSettings: {
                pageLimit: 1000
            }
        };
        if (this.model.get('value')) {
            this.getRoot(this.model.get('value'), itemSelectorSettings);
        } else {
            this.completeInitialization(itemSelectorSettings);
        }
    },

    _getDefaultOutputFolder() {
        const user = getCurrentUser();
        if (!user) {
            return $.Deferred().resolve(null).promise();
        }
        const userFolders = new FolderCollection();
        // find first private one
        return userFolders.fetch({
            parentId: user.id,
            parentType: 'user',
            public: false,
            limit: 1
        }).then(() => {
            if (!userFolders.isEmpty()) {
                return userFolders;
            }
            // find first one including public
            return userFolders.fetch({
                parentId: user.id,
                parentType: 'user',
                limit: 1
            });
        }).then(() => {
            return userFolders.isEmpty() ? null : userFolders.at(0);
        });
    },

    _getDefaultInputResource(model) {
        var type = {image: 'item', item: 'item', file: 'file', directory: 'folder'}[model.get('type')];
        return restRequest({
            url: 'slicer_cli_web/path_match',
            data: {
                type: type,
                name: model.get('defaultNameMatch'),
                path: model.get('defaultPathMatch'),
                relative_path: model.get('defaultRelativePath'),
                base_id: model.get('defaultRelativePath_id'),
                base_type: model.get('defaultRelativePath_type')
            },
            error: null
        }).then((resource) => {
            var ModelType = {image: ItemModel, item: ItemModel, file: FileModel, directory: FolderModel}[model.get('type')];
            const result = new ModelType(resource);
            result._path = resource._path;
            return result;
        });
    },

    /**
     * Trigger a global event to initiate drawing mode to any listener.
     */
    _selectRegion(evt) {
        this.$('.tooltip[role="tooltip"]').remove();
        const target = $(evt.target).closest('.s-select-region-button');
        const submit = target.closest('.input-group-btn').find('.s-select-region-submit-button');
        if (target.hasClass('active')) {
            events.trigger('s:widgetDrawRegionEvent', {model: this.model, mode: null, add: false, submitCtrl: submit, event: evt});
            return;
        }
        const shape = target.attr('shape');
        const multi = target.attr('multi') === 'true';
        events.trigger('s:widgetDrawRegionEvent', {model: this.model, mode: shape, add: multi, submitCtrl: submit, event: evt});
        events.trigger('s:widgetDrawRegion', this.model);
    },

    _clearRegion(evt) {
        this.$('.tooltip[role="tooltip"]').remove();
        const submit = $(evt.target).closest('.input-group-btn').find('.s-select-region-submit-button');
        events.trigger('s:widgetDrawRegionEvent', {model: this.model, mode: null, add: false, submitCtrl: submit, event: evt});
        events.trigger('s:widgetClearRegion', this.model);
    },

    _submitRegionToggle(evt) {
        if ($(evt.target).attr('can-toggle') === 'true') {
            $(evt.target).toggleClass('enabled');
            $(evt.target).toggleClass('active', $(evt.target).hasClass('enabled'));
        }
    }

});

export default ControlWidget;
