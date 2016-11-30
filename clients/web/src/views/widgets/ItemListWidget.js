import $ from 'jquery';
import _ from 'underscore';

import ItemCollection from 'girder/collections/ItemCollection';
import LoadingAnimation from 'girder/views/widgets/LoadingAnimation';
import View from 'girder/views/View';
import { formatSize } from 'girder/misc';

import ItemListTemplate from 'girder/templates/widgets/itemList.pug';

/**
 * This widget shows a list of items under a given folder.
 */
var ItemListWidget = View.extend({
    events: {
        'click a.g-item-list-link': function (event) {
            var cid = $(event.currentTarget).attr('g-item-cid');
            this.trigger('g:itemClicked', this.collection.get(cid), event);
        },
        'click a.g-show-more-items': function () {
            this.collection.fetchNextPage();
        }
    },

    initialize: function (settings) {
        this.checked = [];
        this._checkboxes = settings.checkboxes;
        this._downloadLinks = (
          _.has(settings, 'downloadLinks') ? settings.downloadLinks : true);
        this._viewLinks = (
          _.has(settings, 'viewLinks') ? settings.viewLinks : true);
        this._showSizes = (
          _.has(settings, 'showSizes') ? settings.showSizes : true);

        new LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new ItemCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.on('g:changed', function () {
            this.render();
            this.trigger('g:changed');
        }, this).fetch({
            folderId: settings.folderId
        });
    },

    render: function () {
        this.checked = [];
        this.$el.html(ItemListTemplate({
            items: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            formatSize: formatSize,
            checkboxes: this._checkboxes,
            downloadLinks: this._downloadLinks,
            viewLinks: this._viewLinks,
            showSizes: this._showSizes
        }));

        this.$('.g-item-list-entry a[title]').tooltip({
            container: 'body',
            placement: 'auto',
            delay: 100
        });

        var view = this;
        this.$('.g-list-checkbox').change(function () {
            var cid = $(this).attr('g-item-cid');
            if (this.checked) {
                view.checked.push(cid);
            } else {
                var idx = view.checked.indexOf(cid);
                if (idx !== -1) {
                    view.checked.splice(idx, 1);
                }
            }
            view.trigger('g:checkboxesChanged');
        });
        return this;
    },

    /**
     * Insert an item into the collection and re-render it.
     */
    insertItem: function (item) {
        this.collection.add(item);
        this.trigger('g:changed');
        this.render();
    },

    /**
     * Set all item checkboxes to a certain checked state. The event
     * g:checkboxesChanged is triggered once after checking/unchecking everything.
     * @param {bool} checked The checked state.
     */
    checkAll: function (checked) {
        this.$('.g-list-checkbox').prop('checked', checked);

        this.checked = [];
        if (checked) {
            this.collection.each(function (model) {
                this.checked.push(model.cid);
            }, this);
        }

        this.trigger('g:checkboxesChanged');
    },

    /**
     * Select (highlight) an item in the list.
     * @param item An ItemModel instance representing the item to select.
     */
    selectItem: function (item) {
        this.$('li.g-item-list-entry').removeClass('g-selected');
        this.$('a.g-item-list-link[g-item-cid=' + item.cid + ']')
            .parents('li.g-item-list-entry').addClass('g-selected');
    },

    /**
     * Return the currently selected item, or null if there is no selected item.
     */
    getSelectedItem: function () {
        var el = this.$('li.g-item-list-entry.g-selected');
        if (!el.length) {
            return null;
        }
        var cid = $('.g-item-list-link', $(el[0])).attr('g-item-cid');
        return this.collection.get(cid);
    },

    recomputeChecked: function () {
        this.checked = _.map(this.$('.g-list-checkbox:checked'), function (checkbox) {
            return $(checkbox).attr('g-item-cid');
        }, this);
    }
});

export default ItemListWidget;
