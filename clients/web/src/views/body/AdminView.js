import View from 'girder/views/View';
import { cancelRestRequests } from 'girder/rest';
import { getCurrentUser } from 'girder/auth';

import AdminConsoleTemplate from 'girder/templates/body/adminConsole.pug';

import 'girder/stylesheets/body/adminConsole.styl';

/**
 * This view shows the admin console, which links to all available admin pages.
 */
var AdminView = View.extend({
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

export default AdminView;
