/**
 * This view shows the admin console, which links to all available admin pages.
 */
girder.views.AdminView = Backbone.View.extend({
    events: {
        'click .g-server-config': function () {
            girder.events.trigger('g:navigateTo', girder.views.AdminConfig);
        },
        'click .g-assetstore-config': function () {
            girder.events.trigger('g:navigateTo', girder.views.AssetstoresView);
        }
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
