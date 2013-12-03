/**
 * This view shows a single collection's page.
 */
girder.views.CollectionView = Backbone.View.extend({
    events: {
        'click button.g-collection-edit-button' : function () {
            this.editCollection();
        }
    },

    initialize: function (settings) {
        // If collection model is already passed, there is no need to fetch.
        if (settings.collection) {
            this.model = settings.collection;
            this.render();

            // This page should be re-rendered if the user logs in or out
            girder.events.on('g:login', this.userChanged, this);
        }
        else {
            console.error('Implement fetch then render collection');
        }

    },

    editCollection: function () {
        var container = $('#g-dialog-container');

        if (!this.editCollectionWidget) {
            this.editCollectionWidget = new girder.views.EditCollectionWidget({
                el: container,
                model: this.model
            }).off('g:saved').on('g:saved', function (collection) {
                this.render();
            }, this);
        }
        this.editCollectionWidget.render();
    },

    render: function () {
        this.$el.html(jade.templates.collectionPage({
            collection: this.model,
            girder: girder
        }));

        this.hierarchyWidget = new girder.views.HierarchyWidget({
            parentType: 'collection',
            parentModel: this.model,
            el: this.$('.g-collection-hierarchy-container')
        });

        girder.router.navigate('collection/' + this.model.get('_id'));

        return this;
    },

    userChanged: function () {
        // When the user changes, we should refresh the model to update the
        // _accessLevel attribute on the viewed collection, then re-render the
        // page.
        this.model.off('g:fetched').on('g:fetched', function () {
            this.render();
        }, this).on('g:error', function () {
            // Current user no longer has read access to this user, so we
            // send them back to the user list page.
            girder.events.trigger('g:navigateTo',
                girder.views.CollectionsView);
        }, this).fetch();
    }

});

girder.router.route('collection/:id', 'collection', function (id) {
    // Fetch the collection by id, then render the view.
    var collection = new girder.models.CollectionModel();
    collection.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.CollectionView, {
            collection: collection
        }, collection);
    }, this).on('g:error', function () {
        girder.events.trigger('g:navigateTo', girder.views.CollectionsView);
    }, this).fetch();
});
