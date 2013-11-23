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
        }
    },

    initialize: function () {
        this.collection = new girder.collections.CollectionCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();
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
