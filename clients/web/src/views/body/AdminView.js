import AdminConsoleTemplate from 'girder/templates/body/adminConsole.jade';
import { getCurrentUser } from 'girder/auth';
import { events } from 'girder/events';
import { cancelRestRequests } from 'girder/rest';
import router from 'girder/router';
import View from 'girder/view';

/**
 * This view shows the admin console, which links to all available admin pages.
 */
var AdminView = View.extend({
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
        cancelRestRequests('fetch');
        this.render();
    },

    render: function () {
        if (!getCurrentUser() || !getCurrentUser().get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(AdminConsoleTemplate());

        return this;
    }
});

router.route('admin', 'admin', function () {
    events.trigger('g:navigateTo', AdminView);
});

export default AdminView;
