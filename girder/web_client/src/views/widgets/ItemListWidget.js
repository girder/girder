import $ from 'jquery';
import _ from 'underscore';

import ItemCollection from '@girder/core/collections/ItemCollection';
import LoadingAnimation from '@girder/core/views/widgets/LoadingAnimation';
import View from '@girder/core/views/View';
import { formatSize } from '@girder/core/misc';

import ItemListTemplate from '@girder/core/templates/widgets/itemList.pug';

/**
 * This widget shows a list of items under a given folder.
 */
var ItemListWidget = View.extend({
    events: {
        'click a.g-item-list-link': function (event) {
            event.preventDefault();
            var cid = $(event.currentTarget).attr('g-item-cid');
            this.trigger('g:itemClicked', this.collection.get(cid), event);
        },
        'click a.g-show-more-items': function () {
            this.collection.fetchNextPage();
        },
        'change .g-list-checkbox': function (event) {
            const target = $(event.currentTarget);
            const cid = target.attr('g-item-cid');
            if (target.prop('checked')) {
                this.checked.push(cid);
            } else {
                const idx = this.checked.indexOf(cid);
                if (idx !== -1) {
                    this.checked.splice(idx, 1);
                }
            }
            this.trigger('g:checkboxesChanged');
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
        this.accessLevel = settings.accessLevel;
        this.public = settings.public;

        new LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new ItemCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.filterFunc = settings.itemFilter;

        this.collection.on('g:changed', function () {
            if (this.accessLevel !== undefined) {
                this.collection.each((model) => {
                    model.set('_accessLevel', this.accessLevel);
                });
            }
            this.render();
            this.trigger('g:changed');
        }, this).fetch({ folderId: settings.folderId });
    },

    render: function () {
        this.checked = [];
        this.$el.html(ItemListTemplate({
            items: this.collection.toArray(),
            isParentPublic: this.public,
            hasMore: this.collection.hasNextPage(),
            formatSize: formatSize,
            checkboxes: this._checkboxes,
            downloadLinks: this._downloadLinks,
            viewLinks: this._viewLinks,
            showSizes: this._showSizes
        }));

        return this;
    },

    /**
     * Insert an item into the collection and re-render it.
     */
    insertItem: function (item) {
        if (this.accessLevel !== undefined) {
            item.set('_accessLevel', this.accessLevel);
        }
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
