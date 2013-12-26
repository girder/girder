/**
 * This view shows a single item's page.
 */
girder.views.ItemView = Backbone.View.extend({
    events: {
        'click .g-edit-item': 'editItem',
    },

    initialize: function (settings) {
        // If collection model is already passed, there is no need to fetch.
        if (settings.item) {
            this.model = settings.item;
            this.render();

            // This page should be re-rendered if the user logs in or out
            girder.events.on('g:login', this.userChanged, this);
        }
        else {
            console.error('Implement fetch then render item');
        }

    },

    editItem: function () {
        var container = $('#g-dialog-container');

        if (!this.editItemWidget) {
            this.editItemWidget = new girder.views.EditItemWidget({
                el: container,
                model: this.model
            }).off('g:saved').on('g:saved', function (item) {
                this.render();
            }, this);
        }
        this.editItemWidget.render();
    },

    render: function () {
        this.$el.html(jade.templates.itemPage({
            item: this.model,
            girder: girder
        }));


        girder.router.navigate('item/' + this.model.get('_id'));

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
    },

});

girder.router.route('item/:id', 'item', function (id) {
    // Fetch the collection by id, then render the view.
    var item = new girder.models.ItemModel();
    item.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.ItemView, {
            item: item
        }, item);
    }, this).on('g:error', function () {
        girder.events.trigger('g:navigateTo', girder.views.CollectionsView);
    }, this).fetch();
});
