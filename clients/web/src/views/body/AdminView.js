var girder               = require('girder/init');
var AdminConsoleTemplate = require('girder/templates/body/adminConsole.jade');
var Auth                 = require('girder/auth');
var Events               = require('girder/events');
var Rest                 = require('girder/rest');
var View                 = require('girder/view');

/**
 * This view shows the admin console, which links to all available admin pages.
 */
var AdminView = View.extend({
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
        Rest.cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        if (!Auth.getCurrentUser() || !Auth.getCurrentUser().get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(AdminConsoleTemplate());

        return this;
    }
});

module.exports = AdminView;

girder.router.route('admin', 'admin', function () {
    Events.trigger('g:navigateTo', AdminView);
});
