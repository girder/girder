/**
 * This view lists the collections.
 */
girder.views.CollectionsView = girder.View.extend({
    events: {
        'click a.g-collection-link': function (event) {
            var cid = $(event.currentTarget).attr('g-collection-cid');
            girder.router.navigate('collection/' + this.collection.get(cid).id, {trigger: true});
        },
        'click button.g-collection-create-button': function (event) {
            this.createCollectionDialog();
        },
        'submit .g-collections-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function (settings) {
        this.collection = new girder.collections.CollectionCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.create = settings.dialog === 'create';
    },

    /**
     * Prompt the user to create a new collection
     */
    createCollectionDialog: function () {
        var container = $('#g-dialog-container');

        new girder.views.EditCollectionWidget({
            el: container
        }).off('g:saved').on('g:saved', function (collection) {
            girder.router.navigate('collection/' + collection.get('_id'),
                                   {trigger: true});
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

        if (this.create) {
            this.createCollectionDialog();
        }

        return this;
    },

    /**
     * When the user clicks a search result collection, this helper method
     * will navigate them to the view for that specific collection.
     */
    _gotoCollection: function (result) {
        var collection = new girder.models.CollectionModel();
        collection.set('_id', result.id).on('g:fetched', function () {
            girder.router.navigate('/collection/' + this.id, {trigger: true});
        }, this).fetch();
    }
});

girder.router.route('collections', 'collections', function (params) {
    girder.events.trigger('g:navigateTo', girder.views.CollectionsView, params || {});
    girder.events.trigger('g:highlightItem', 'CollectionsView');
});
