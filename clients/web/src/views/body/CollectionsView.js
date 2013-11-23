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
    },

    /**
     * Prompt the user to create a new collection
     */
    createFolderDialog: function () {
        var container = $('#g-dialog-container');

        if (!this.editCollectionWidget) {
            this.editCollectionWidget = new girder.views.EditCollectionWidget({
                el: container
            }).off('g:saved').on('g:saved', function (collection) {
                this.insertCollection(collection);
            }, this);
        }
        this.editCollectionWidget.render();
    },

    /**
     * Add a new collection to the system
     */
    insertCollection: function (collection) {
        console.log(collection);
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
    }
});

girder.router.route('collections', 'collections', function () {
    girder.events.trigger('g:navigateTo', girder.views.CollectionsView);
    girder.events.trigger('g:highlightItem', 'CollectionsView');
});
