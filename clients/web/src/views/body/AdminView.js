/**
 * This view shows a single user's page.
 */
girder.views.AdminView = Backbone.View.extend({
    events: {
    },

    initialize: function () {
        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.render, this);
        this.render();
    },

    render: function () {
        if (!girder.currentUser || !girder.currentUser.get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(jade.templates.adminConsole());

        girder.router.navigate('admin');

        return this;
    }
});

girder.router.route('admin', 'admin', function () {
    girder.events.trigger('g:navigateTo', girder.views.AdminView);
});
