import ItemCollection from 'girder/collections/ItemCollection';
import View from 'girder/views/View';
import { restRequest, apiRoot } from 'girder/rest';

import ItemPreviewWidgetTemplate from '../templates/itemPreviewWidget.pug';
import ItemPreviewItemTemplate from '../templates/itemPreviewItem.pug';
import '../stylesheets/itemPreviewWidget.styl';

/**
 * The Item Preview widget shows a preview of items under a given folder.
 * For now, this only support json and images file types.
 */
var ItemPreviewWidget = View.extend({
    events: {
        'click a.g-item-preview-link': function (event) {
            var id = this.$(event.currentTarget).data('id');
            this.parentView.itemListView.trigger('g:itemClicked', this.collection.get(id));
        }
    },

    initialize: function (settings) {
        this._isSupportedItem = this._isSupportedItem.bind(this);
        this.debouncedAddMoreItem = _.debounce(this.addMoreItem, 100);

        this.initialized = false;

        this.addingMoreItems = false;

        this.supportedItems = [];

        this.collection = settings.collection;
        this.collection.on('g:changed', () => {
            this.supportedItems = this.collection.toJSON().filter(this._isSupportedItem);
            if (this.supportedItems.length != 0 &&
                this.isNotFull()) {
                this.debouncedAddMoreItem();
            }
        });
    },

    _MAX_JSON_SIZE: 2e6 /* bytes */,
    _LOAD_BATCH_SIZE: 1,

    _isSupportedItem: function (item) {
        return this._isImageItem(item.name) || this._isJSONItem(item.name);
    },

    _isJSONItem: function (str) {
        return /(json)$/i.test(str);
    },

    _isImageItem: function (str) {
        return /(jpg|jpeg|png|gif)$/i.test(str);
    },

    setElement: function ($el) {
        this.initialized = false;
        View.prototype.setElement.apply(this, arguments);
    },

    render: function () {
        if (!this.initialized) {
            this.initialized = true;
            this.renderedIndex = 0;
            this.$el.html(ItemPreviewWidgetTemplate(this));
            this.$('.g-widget-item-previews-container').on('scroll', e => this.onScroll(e));
            this.debouncedAddMoreItem();
        }
    },

    isNotFull: function () {
        return this.$('.g-widget-item-prevews-wrapper').height() <= this.$('.g-widget-item-previews-container').height();
    },

    allItemAdded: function () {
        return this.renderedIndex == this.supportedItems.length;
    },

    addMoreItem: function () {
        this.addingMoreItems = true;
        var items = this.supportedItems.slice(this.renderedIndex, this.renderedIndex + this._LOAD_BATCH_SIZE);
        this.renderedIndex = Math.min(this.renderedIndex + this._LOAD_BATCH_SIZE, this.supportedItems.length);

        var $container = this.$('.g-widget-item-prevews-wrapper');

        Promise.all(items.map(item => {
            return new Promise((resolve, reject) => {
                restRequest({
                    path: `item/${item._id}/download`,
                    type: 'HEAD',
                    complete: function (xhr) {
                        var contentType = xhr.getResponseHeader('Content-Type');
                        resolve([item, contentType]);
                    }
                })
            }).then(([item, contentType]) => {
                if (contentType == 'application/zip') {
                    return Promise.resolve(restRequest({
                        path: `item/${item._id}/files`,
                    })).then(files => {
                        return Promise.all(files.map(file => {
                            return this.tryGetItemOrFileContent(file, file.mimeType, 'file');
                        }))
                    })
                }
                else {
                    return Promise.all([this.tryGetItemOrFileContent(item, contentType, 'item')]);
                }
            })
        })).then(results => {
            items.forEach((item, i) => {
                var contents = results[i].filter(result => result);
                if (contents.length) {
                    $container.append(ItemPreviewItemTemplate({
                        item: item,
                        contents: contents
                    }));
                }
            });
            this.addingMoreItems = false;

            // In case the container is not fully filled add more items
            if (!this.allItemAdded() && this.isNotFull()) {
                this.addMoreItem();
            }
        });
    },

    onScroll: function (e) {
        var $wrapper = $(e.target);
        if ($wrapper.scrollTop() + $wrapper.innerHeight() >= $wrapper[0].scrollHeight - 200) {
            if (!this.addingMoreItems && !this.allItemAdded()) {
                this.addMoreItem();
            }
        }
    },

    tryGetItemOrFileContent: function (record, contentType, type) {
        if (this._isJSONItem(record.name) && contentType == 'application/octet-stream') {
            if (record.size > this._MAX_JSON_SIZE) {
                return Promise.resolve(null);
            }
            return this.getJsonContent(`${type}/${record._id}/download`);
        }
        else if (this._isImageItem(contentType)) {
            return this.getImageContent(`${type}/${record._id}/download`);
        }
    },

    getJsonContent: function (url) {
        return Promise.resolve(restRequest({
            path: url,
            type: 'GET',
            error: null
        })).then(resp => {
            return {
                type: 'json',
                value: resp
            };
        });
    },

    getImageContent: function (url) {
        // preload image to help evaluate height and avoid jumpy behavior
        return new Promise((resolve, reject) => {
            var src = apiRoot + '/' + url;
            var image = new Image();
            image.onload = function () {
                resolve({
                    type: 'image',
                    value: src
                })
            }
            image.src = src;
        });
    }

});

export default ItemPreviewWidget;
