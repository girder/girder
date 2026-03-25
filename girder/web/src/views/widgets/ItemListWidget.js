import $ from 'jquery';
import _ from 'underscore';

import ItemCollection from '@girder/core/collections/ItemCollection';
import LoadingAnimation from '@girder/core/views/widgets/LoadingAnimation';
import View from '@girder/core/views/View';
import { formatSize } from '@girder/core/misc';
import { restRequest } from '@girder/core/rest';

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
        this._highlightItem = (
            _.has(settings, 'highlightItem') ? settings.highlightItem : false);
        this._paginated = (
            _.has(settings, 'paginated') ? settings.paginated : false);

        this.accessLevel = settings.accessLevel;
        this.public = settings.public;
        this._selectedItem = settings.selectedItem;

        new LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new ItemCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.filterFunc = settings.itemFilter;
        this.currentPage = 1; // By default we want to be on the first page

        if (this._paginated) {
            if (this.collection.filterFunc) {
                console.warn('Pagination cannot be used with a filter function');
                this._paginated = false;
            } else {
                // Override the default to prevent appending new pages
                this.collection.append = false;
            }
        }

        this.collection.fetch({ folderId: settings.folderId }).done(() => {
            this._totalPages = Math.ceil(this.collection.getTotalCount() / this.collection.pageLimit);
            if (this._paginated && this.collection.hasNextPage()) {
                // Tells the parent container that the item is paginated so it can render the page selector
                this.trigger('g:paginated');
                // We need to get the position in the list for the selected item
                if (this._selectedItem) {
                    restRequest({
                        url: `item/${this._selectedItem.get('_id')}/position`,
                        method: 'GET',
                        data: { folderId: this._selectedItem.get('folderId'), sort: 'name' }
                    }).done((val) => {
                        // Now we fetch the correct page for the position
                        val = Number(val);
                        if (val >= this.collection.pageLimit) {
                            const pageLimit = this.collection.pageLimit;
                            const calculatedPage = 1 + Math.ceil((val - (val % pageLimit)) / pageLimit);
                            return this.collection.fetchPage(calculatedPage - 1);
                        }
                    }).done(() => this.bindOnChanged());
                } else {
                    this.bindOnChanged();
                }
            } else {
                this.bindOnChanged();
            }
        });
    },

    /**
     * Binds the change function to the collection and calls it initially to update the render
     */
    bindOnChanged: function () {
        this.collection.on('g:changed', this.changedFunc, this);
        this.changedFunc();
    },
    /**
     * Function that causes a render each time the collection is changed
     * Will also update the current page in a paginated system
     */
    changedFunc: function () {
        if (this.accessLevel !== undefined) {
            this.collection.each((model) => {
                model.set('_accessLevel', this.accessLevel);
            });
        }
        if (this._paginated) {
            this.currentPage = this.collection.pageNum() + 1;
        }
        this.render();
        this.trigger('g:changed');
    },

    render: function () {
        this.checked = [];
        // If we set a selected item in the beginning we will center the selection while loading
        if (this._selectedItem && this._highlightItem) {
            this.scrollPositionObserver();
        }

        this.$el.html(ItemListTemplate({
            items: this.collection.toArray(),
            isParentPublic: this.public,
            hasMore: this.collection.hasNextPage(),
            formatSize: formatSize,
            checkboxes: this._checkboxes,
            downloadLinks: this._downloadLinks,
            viewLinks: this._viewLinks,
            showSizes: this._showSizes,
            highlightItem: this._highlightItem,
            selectedItemId: (this._selectedItem || {}).id,
            paginated: this._paginated

        }));

        return this;
    },

    /**
     * @returns {number} the number of pages in the itemList for use in a paginated view
     */
    getNumPages() {
        return this._totalPages || 1;
    },
    /**
     * @returns {number} the current page for paginated lists, defaults to 1 if none is provided
     */
    getCurrentPage() {
        return this.currentPage || 1;
    },
    /**
     * Externally facing function to allow hierarchyWidget and others to set the current page if the item is paginated
     * @param {Number} page 1 index integer specifying the page to fetch
     */
    setPage(page) {
        if (this._paginated && this.collection && this.collection.fetchPage) {
            this.currentPage = page;
            return this.collection.fetchPage(page - 1).then(() =>
                this.$el.parents('.g-hierarchy-widget-container').scrollTop(0));
        }
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
    },

    centerSelected: function () {
        const widgetcontainer = this.$el.parents('.g-hierarchy-widget-container');
        const selected = this.$('li.g-item-list-entry.g-selected');
        if (widgetcontainer.length > 0 && selected.length > 0) {
            // These items will effect the scroll position if they exists
            const folderHeight  = $('.g-folder-list').length ? $('.g-folder-list').height() : 0;
            const breadcrumbHeight = $('.g-hierarchy-breadcrumb-bar').length ? $('.g-hierarchy-breadcrumb-bar').height() : 0;
            const selectedTop = selected.position().top;
            // The selectedTop position needs to account for the breadcrumbHeight and the folderHeight
            const scrollingPos = selectedTop + folderHeight + breadcrumbHeight;
            const centerPos = (widgetcontainer.height() / 2.0) - (folderHeight / 2.0) - (breadcrumbHeight / 2.0) - (selected.outerHeight() / 2.0);

            const scrollPos = scrollingPos - centerPos;
            if (this.tempScrollPos === undefined) {
                this.tempScrollPos = scrollPos;
            }
            // Call a custom scroll event to prevent thinking the user initiated it
            const e = new CustomEvent('scroll', { detail: 'selected_item_scroll' });
            widgetcontainer[0].scrollTop = scrollPos;
            widgetcontainer[0].dispatchEvent(e);
        }
    },
    /**
     * This will look at the position of the selected item and update it as images load and
     * the DOM reflows
     */
    scrollPositionObserver: function () {
        // Set the default selected height for the selected item
        const target = this.$('.g-item-list');
        if (window.MutationObserver && target.length > 0) {
            // Default items to monitor for the scroll position
            const widgetcontainer = this.$el.parents('.g-hierarchy-widget-container');
            // If the observer already exists disconnect it so it can be recreated
            if (this.observer && this.observer.disconnect) {
                this.observer.disconnect();
            }

            // Event handler for loading images declared once
            const onLoadImage = () => {
                if (this.observer) {
                    this.centerSelected();
                }
            };

            this.observer = new MutationObserver((mutations) => {
                // for every mutation
                _.each(mutations, (mutation) => {
                    // If no nodes are added we can return
                    if (!mutation.addedNodes) {
                        return;
                    }

                    // for every added node
                    _.each(mutation.addedNodes, (node) => {
                        if (node.className && node.className.indexOf('g-item-list') !== -1) {
                            // We want to do a onetime scroll to position if the screen is idle
                            if (window.requestIdleCallback) {
                                // Processing time is 2 seconds, but should finish much faster
                                requestIdleCallback(() => {
                                    this.centerSelected();
                                }, { timeout: 2000 });
                            } else {
                                this.centerSelected();
                            }
                        }

                        // For any images added we wait until loaded and rescroll to the selected
                        if (_.isFunction(node.getElementsByTagName)) {
                            this.$('img', node).on('load', onLoadImage);
                        }
                    });
                });
            });

            // bind mutation observer to a specific element (probably a div somewhere)
            this.observer.observe(target.parent()[0], { childList: true, subtree: true });

            // Remove event listeners and disconnect observer
            const unbindDisconnect = () => {
                if (this.observer) {
                    widgetcontainer.unbind('scroll.observerscroll');
                    widgetcontainer.unbind('wheel.observerscroll');
                    widgetcontainer.unbind('click.observerscroll');
                    this.observer.disconnect();
                    this.observer = null;
                    this.tempScrollPos = undefined;
                    // Prevents scrolling when user clicks 'show more...'
                    this._highlightItem = false;
                }
            };

            // Add in scroll event to monitor the scrollPos to prevent unnecessary updates and also kill observer when user scrolls
            widgetcontainer.bind('scroll.observerscroll', (evt) => {
                if (this.tempScrollPos !== undefined && this.tempScrollPos !== widgetcontainer[0].scrollTop) {
                    this.tempScrollPos = widgetcontainer[0].scrollTop;
                    // If the event detail is not 'selected_item_scroll' the scroll should be a user initiated scroll
                    if (evt.detail !== 'selected_item_scroll') {
                        unbindDisconnect();
                    }
                }
            });
            // Backup function to kill observer if user clicks an item, moves scrollwheel, or touchpad equivalent
            widgetcontainer.bind('wheel.selectionobserver', unbindDisconnect);
            widgetcontainer.bind('click.selectionobserver', unbindDisconnect);
        }
    }
});

export default ItemListWidget;
