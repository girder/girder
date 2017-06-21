import _ from 'underscore';
import $ from 'jquery';
import View from 'girder/views/View';
import { restRequest, apiRoot } from 'girder/rest';
import { _whenAll } from 'girder/misc';

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
    },

    // Because the parent-child life cycle is not clean, this method is needed.
    setCollection: function (collection) {
        this.collection = collection;
        this.collection.on('g:changed', () => {
            this.supportedItems = this.collection.toJSON().filter(this._isSupportedItem);
            if (this.supportedItems.length !== 0 &&
                (this.isNotFull() || this.isNearBottom())) {
                this.debouncedAddMoreItem();
            }
        });
    },

    _MAX_JSON_SIZE: 2e6 /* bytes */,
    _LOAD_BATCH_SIZE: 2,

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
            this.$('.g-widget-item-previews-container').on('scroll', (e) => this.onScroll(e));
            this.debouncedAddMoreItem();
        }
    },

    isNotFull: function () {
        return this.$('.g-widget-item-prevews-wrapper').height() <= this.$('.g-widget-item-previews-container').height();
    },

    allItemAdded: function () {
        return this.renderedIndex === this.supportedItems.length;
    },

    addMoreItem: function () {
        this.addingMoreItems = true;
        var items = this.supportedItems.slice(this.renderedIndex, this.renderedIndex + this._LOAD_BATCH_SIZE);
        this.renderedIndex = Math.min(this.renderedIndex + this._LOAD_BATCH_SIZE, this.supportedItems.length);

        if (!items.length) {
            return;
        }

        var $container = this.$('.g-widget-item-prevews-wrapper');
        _whenAll(items.map((item) => {
            return restRequest({
                path: `item/${item._id}/files`
            }).then((files) => {
                return _whenAll(files.map((file) => {
                    return this.tryGetFileContent(file, file.mimeType, 'file');
                }));
            });
        })).then((results) => {
            items.forEach((item, i) => {
                var contents = results[i].filter((result) => result);
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
            return undefined;
        });
    },

    isNearBottom: function () {
        var $container = this.$('.g-widget-item-previews-container');
        return $container.scrollTop() + $container.innerHeight() >= $container[0].scrollHeight - 200;
    },

    onScroll: function (e) {
        if (this.isNearBottom()) {
            if (!this.addingMoreItems && !this.allItemAdded()) {
                this.addMoreItem();
            }
        }
    },

    tryGetFileContent: function (file, contentType, type) {
        if (this._isJSONItem(file.name) && contentType === 'application/octet-stream') {
            if (file.size > this._MAX_JSON_SIZE) {
                return $.Defrred().resolve(null).promise();
            }
            return this.getJsonContent(`${type}/${file._id}/download`);
        } else if (this._isImageItem(contentType)) {
            return this.getImageContent(`${type}/${file._id}/download`);
        }
    },

    getJsonContent: function (url) {
        return restRequest({
            path: url,
            type: 'GET',
            error: null
        }).then((resp) => {
            return {
                type: 'json',
                value: resp
            };
        });
    },

    getImageContent: function (url) {
        // preload image to help evaluate height and avoid jumpy behavior
        var deferred = $.Deferred();
        var src = apiRoot + '/' + url;
        var image = new Image();
        image.onload = function () {
            deferred.resolve({
                type: 'image',
                value: src
            });
        };
        image.src = src;
        return deferred.promise();
    }
});

export default ItemPreviewWidget;
