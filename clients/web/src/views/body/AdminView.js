/**
 * This view shows the admin console, which links to all available admin pages.
 */
girder.views.AdminView = girder.View.extend({
    events: {
        'click .g-server-config': function () {
            girder.router.navigate('settings', {trigger: true});
        },
        'click .g-assetstore-config': function () {
            girder.router.navigate('assetstores', {trigger: true});
        },
        'click .g-plugins-config': function () {
            girder.router.navigate('plugins', {trigger: true});
        }
    },

    initialize: function () {
        girder.cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        if (!girder.currentUser || !girder.currentUser.get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(girder.templates.adminConsole());

        return this;
    }
});

girder.router.route('admin', 'admin', function () {
    girder.events.trigger('g:navigateTo', girder.views.AdminView);
});
