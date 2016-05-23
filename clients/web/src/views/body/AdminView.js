import AdminConsoleTemplate from 'girder/templates/body/adminConsole.jade';
import Auth                 from 'girder/auth';
import Events               from 'girder/events';
import Rest                 from 'girder/rest';
import router               from 'girder/router';
import View                 from 'girder/view';

/**
 * This view shows the admin console, which links to all available admin pages.
 */
export var AdminView = View.extend({
    events: {
        'click .g-server-config': function () {
            router.navigate('settings', {trigger: true});
        },
        'click .g-assetstore-config': function () {
            router.navigate('assetstores', {trigger: true});
        },
        'click .g-plugins-config': function () {
            router.navigate('plugins', {trigger: true});
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

router.route('admin', 'admin', function () {
    Events.trigger('g:navigateTo', AdminView);
});
