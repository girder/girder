import ItemCollection from 'girder/collections/ItemCollection';
import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import ItemPreviewWidgetTemplate from '../templates/itemPreviewWidget.pug';
import '../stylesheets/itemPreviewWidget.styl';

/**
 * The Item Preview widget shows a preview of items under a given folder.
 * For now, the only supported item previews are image previews.
 */
var ItemPreviewWidget = View.extend({
    events: {
        'click a.g-item-preview-link': function (event) {
            var id = this.$(event.currentTarget).data('id');
            this.parentView.itemListView.trigger('g:itemClicked', this.collection.get(id));
        },
        'click .g-widget-item-previews-wrap': function (event) {
            this.wrapPreviews = !this.wrapPreviews;
            this.render();
            if (this.wrapPreviews) {
                this.$('.g-widget-item-previews-container').addClass('g-wrap');
            } else {
                this.$('.g-widget-item-previews-container').removeClass('g-wrap');
            }
        }
    },

    initialize: function (settings) {
        this.collection = new ItemCollection();
        this.itemCollection = {};

        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.loadFileList();
        }, this).fetch({
            folderId: settings.folderId
        });

        this.wrapPreviews = false;
    },

    _MAX_JSON_SIZE: 2e6 /* bytes */,

    _isSupportedItem: function (item) {
        return this._isImageItem(item) || this._isJSONItem(item);
    },

    _isJSONItem: function (item) {
        return /\.(json)$/i.test(item.get('name'));
    },

    _isImageItem: function (item) {
        return /\.(jpg|jpeg|png|gif)$/i.test(item.get('name'));
    },

    _isSingleFileItem: function (item) {
        return this.itemCollection[item.get('_id')].length === 1;
    },

    loadFileList: function () {
        var count = 0;
        var view = this;
        this.collection.forEach(function (item) {
            restRequest({
                path: `/item/${item.id}/files`
            }).done(resp => {
                // add files data to itemCollection
                view.itemCollection[item.get('_id')] = resp;

                // when all files from items are fetched --> render
                if (count === view.collection.length - 1) {
                    view.render();
                } else {
                    count++;
                }
            });
        });
    },

    render: function () {
        var supportedItems = this.collection.filter(this._isSupportedItem.bind(this));

        // do not support preview for multiples files inside item
        supportedItems = supportedItems.filter(this._isSingleFileItem.bind(this));

        var view = this;

        view.$el.html(ItemPreviewWidgetTemplate({
            items: supportedItems,
            wrapPreviews: view.wrapPreviews,
            hasMore: this.collection.hasNextPage(),
            isImageItem: this._isImageItem,
            isJSONItem: this._isJSONItem
        }));

        // Render any JSON files.
        supportedItems.filter(this._isJSONItem).forEach(function (item) {
            var id = item.get('_id');

            // Don't process JSON files that are too big to preview.
            var size = item.get('size');
            if (size > this._MAX_JSON_SIZE) {
                return view.$('.json[data-id="' + id + '"]').text('JSON too big to preview.');
            }

            // Ajax request the JSON files to display them.
            restRequest({
                path: 'item/' + id + '/download',
                type: 'GET',
                error: null // don't do default error behavior (validation may fail)
            }).done(function (resp) {
                view.$('.json[data-id="' + id + '"]').text(JSON.stringify(resp, null, '\t'));
            }).fail(function (err) {
                console.error('Could not preview item', err);
            });
        });

        this.$('.g-widget-item-previews-wrap').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }

});

export default ItemPreviewWidget;
