/**
 * This widget shows a list of items under a given folder.
 */
girder.views.ItemListWidget = girder.View.extend({
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

        new girder.views.LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new girder.collections.ItemCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.render();
        }, this).fetch({
            folderId: settings.folderId
        });
    },

    render: function () {
        this.checked = [];
        this.$el.html(girder.templates.itemList({
            items: this.collection.models,
            hasMore: this.collection.hasNextPage(),
            girder: girder,
            checkboxes: this._checkboxes
        }));

        var view = this;
        this.$('.g-list-checkbox').unbind('change').change(function () {
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
            _.each(this.collection.models, function (model) {
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
    }
});
