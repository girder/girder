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
            this.createFolderDialog();
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
    createFolderDialog: function () {
        var container = $('#g-dialog-container');

        new girder.views.EditCollectionWidget({
            el: container
        }).off('g:saved').on('g:saved', function (collection) {
            this.insertCollection(collection);
        }, this).render();
    },

    /**
     * Add a new collection to the system
     */
    insertCollection: function (collection) {
        this.collection.add(collection);
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.collectionList({
            collections: this.collection.models,
            girder: girder
        }));
        girder.router.navigate('collections');

        return this;
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
