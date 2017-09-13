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
 * For now, this only supports json and images file types.
 */
var ItemPreviewWidget = View.extend({
    events: {
        'click a.g-item-preview-link': function (event) {
            var id = this.$(event.currentTarget).data('id');
            this.parentView.itemListView.trigger('g:itemClicked', this.collection.get(id));
        }
    },

    initialize: function (settings) {
        this.debouncedaddMoreItems = _.debounce(this.addMoreItems, 100);
        this.onScroll = _.debounce(this.onScroll, 100);

        this.initialized = false;

        this.addingMoreItems = false;

        this.supportedItems = [];
    },

    // Because the parent-child life cycle is not clean, this method is needed.
    setCollection: function (collection) {
        this.collection = collection;
        this.listenTo(this.collection, 'g:changed', () => {
            this.supportedItems = this.collection.toJSON().filter(this._isSupportedItem.bind(this));
            if (this.supportedItems.length !== 0 &&
                (this.isNotFull() || this.isNearBottom())) {
                this.debouncedaddMoreItems();
            }
        });
    },

    _MAX_JSON_SIZE: 2e6 /* bytes */,
    _MAX_IMAGE_SIZE: 2e7 /* bytes */,
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
        return View.prototype.setElement.apply(this, arguments);
    },

    render: function () {
        if (!this.initialized) {
            this.initialized = true;
            this.renderedIndex = 0;
            this.$el.html(ItemPreviewWidgetTemplate());
            this.$('.g-widget-item-previews-container').on('scroll', (e) => this.onScroll(e));
            this.debouncedaddMoreItems();
        }
        return this;
    },

    isNotFull: function () {
        return this.$('.g-widget-item-previews-wrapper').height() <= this.$('.g-widget-item-previews-container').height();
    },

    allItemAdded: function () {
        return this.renderedIndex >= this.supportedItems.length;
    },

    addMoreItems: function () {
        this.addingMoreItems = true;
        var items = this.supportedItems.slice(this.renderedIndex, this.renderedIndex + this._LOAD_BATCH_SIZE);
        this.renderedIndex = Math.min(this.renderedIndex + this._LOAD_BATCH_SIZE, this.supportedItems.length);

        if (!items.length) {
            return;
        }

        var $container = this.$('.g-widget-item-previews-wrapper');
        _whenAll(items.map((item) => {
            return restRequest({
                url: `item/${item._id}/files`,
                data: { limit: 5 }
            }).then((files) => {
                return _whenAll(files.map((file) => {
                    return this.tryGetFileContent(file, file.mimeType);
                }));
            });
        })).done((results) => {
            items.forEach((item, i) => {
                var contents = results[i].filter((result) => result);
                if (contents.length) {
                    $container.append(ItemPreviewItemTemplate({
                        item: item,
                        contents: contents
                    }));
                }
            });

            // In case the container is not fully filled add more items
            if (!this.allItemAdded() && this.isNotFull()) {
                this.addMoreItems();
            }
        }).always(() => {
            this.addingMoreItems = false;
        });
    },

    isNearBottom: function () {
        var $container = this.$('.g-widget-item-previews-container');
        return $container.scrollTop() + $container.innerHeight() >= $container[0].scrollHeight - 200;
    },

    onScroll: function (e) {
        if (this.isNearBottom() && !this.addingMoreItems && !this.allItemAdded()) {
            this.addMoreItems();
        }
    },

    tryGetFileContent: function (file, contentType) {
        if (this._isJSONItem(file.name)) {
            if (file.size > this._MAX_JSON_SIZE) {
                return $.Deferred().resolve(null).promise();
            }
            return this.getJsonContent(`file/${file._id}/download`);
        } else if (this._isImageItem(contentType)) {
            if (file.size > this._MAX_IMAGE_SIZE) {
                return $.Deferred().resolve(null).promise();
            }
            return this.getImageContent(`file/${file._id}/download`);
        }
    },

    getJsonContent: function (url) {
        return restRequest({
            url: url,
            method: 'GET',
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
