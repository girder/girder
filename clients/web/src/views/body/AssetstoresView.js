/**
 * This view shows the admin console, which links to all available admin pages.
 */
girder.views.AssetstoresView = Backbone.View.extend({
    events: {

    },

    initialize: function () {
        // Fetch all of the current assetstores
        if (girder.currentUser && girder.currentUser.get('admin')) {
            this.collection = new girder.collections.AssetstoreCollection();
            this.collection.on('g:changed', function () {
                this.render();
            }, this).fetch();
        }
        else {
            this.render();
        }
        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.render, this);
    },

    render: function () {
        if (!girder.currentUser || !girder.currentUser.get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(jade.templates.assetstores());

        girder.router.navigate('assetstores');

        return this;
    }
});

girder.router.route('assetstores', 'assetstores', function () {
    girder.events.trigger('g:navigateTo', girder.views.AssetstoresView);
});
