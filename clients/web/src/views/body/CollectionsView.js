/**
 * This view lists the collections.
 */
girder.views.CollectionsView = Backbone.View.extend({
    events: {
        'click a.g-collection-link': function (event) {
            var cid = $(event.currentTarget).attr('g-collection-cid');
            var params = {
                collection: this.collection.get(cid)
            };
            girder.events.trigger('g:navigateTo', girder.views.CollectionView,
                params);
        },
        'click button.g-collection-create-button': function (event) {
            this.createCollectionDialog();
        },
        'submit .g-collections-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function () {
        this.collection = new girder.collections.CollectionCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.userChanged, this);
    },

    /**
     * Prompt the user to create a new collection
     */
    createCollectionDialog: function () {
        var container = $('#g-dialog-container');

        new girder.views.EditCollectionWidget({
            el: container
        }).off('g:saved').on('g:saved', function (collection) {
            girder.events.trigger('g:navigateTo', girder.views.CollectionView, {
                collection: collection
            });
        }, this).render();
    },

    render: function () {
        this.$el.html(jade.templates.collectionList({
            collections: this.collection.models,
            girder: girder
        }));

        new girder.views.PaginateWidget({
            el: this.$('.g-collection-pagination'),
            collection: this.collection
        }).render();

        new girder.views.SearchFieldWidget({
            el: this.$('.g-collections-search-container'),
            placeholder: 'Search collections...',
            types: ['collection']
        }).off().on('g:resultClicked', this._gotoCollection, this).render();

        girder.router.navigate('collections');

        return this;
    },

    /**
     * When the user clicks a search result collection, this helper method
     * will navigate them to the view for that specific collection.
     */
    _gotoCollection: function (result) {
        var collection = new girder.models.CollectionModel();
        collection.set('_id', result.id).on('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.CollectionView, {
                collection: collection
            });
        }, this).fetch();
    },

    userChanged: function () {
        // When the user changes, we should refresh the page to reveal the
        // appropriate collections
        this.collection.reset();
        this.collection.off('g:fetched').on('g:fetched', function () {
            this.render();
        }, this).fetch();
    }
});

girder.router.route('collections', 'collections', function () {
    girder.events.trigger('g:navigateTo', girder.views.CollectionsView);
    girder.events.trigger('g:highlightItem', 'CollectionsView');
});
