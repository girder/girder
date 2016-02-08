/**
 * This view lists the collections.
 */
girder.views.CollectionsView = girder.View.extend({
    events: {
        'click a.g-collection-link': function (event) {
            var cid = $(event.currentTarget).attr('g-collection-cid');
            girder.router.navigate('collection/' + this.collection.get(cid).id, {trigger: true});
        },
        'click button.g-collection-create-button': 'createCollectionDialog',
        'submit .g-collections-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function (settings) {
        girder.cancelRestRequests('fetch');
        this.collection = new girder.collections.CollectionCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = new girder.views.PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = new girder.views.SearchFieldWidget({
            placeholder: 'Search collections...',
            types: ['collection'],
            parentView: this
        }).on('g:resultClicked', this._gotoCollection, this);

        this.create = settings.dialog === 'create';
    },

    /**
     * Prompt the user to create a new collection
     */
    createCollectionDialog: function () {
        var container = $('#g-dialog-container');

        new girder.views.EditCollectionWidget({
            el: container,
            parentView: this
        }).on('g:saved', function (collection) {
            girder.router.navigate('collection/' + collection.get('_id'),
                                   {trigger: true});
        }, this).render();
    },

    render: function () {
        this.$el.html(girder.templates.collectionList({
            collections: this.collection.toArray(),
            girder: girder
        }));

        this.paginateWidget.setElement(this.$('.g-collection-pagination')).render();
        this.searchWidget.setElement(this.$('.g-collections-search-container')).render();

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
            girder.router.navigate('/collection/' + collection.get('_id'), {trigger: true});
        }, this).fetch();
    }
});

girder.router.route('collections', 'collections', function (params) {
    girder.events.trigger('g:navigateTo', girder.views.CollectionsView, params || {});
    girder.events.trigger('g:highlightItem', 'CollectionsView');
});
