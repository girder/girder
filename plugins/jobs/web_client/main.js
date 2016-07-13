import { wrap } from 'girder/utilities/PluginUtils';
import { getCurrentUser } from 'girder/auth';
import LayoutHeaderUserView from 'girder/views/layout/HeaderUserView';

import './routes';

/**
 * Add an entry to the user dropdown menu to navigate to user's job list view.
 */
import jobs_userMenu from './templates/jobs_userMenu.jade';
wrap(LayoutHeaderUserView, 'render', function (render) {
    render.call(this);

    var currentUser = getCurrentUser();
    if (currentUser) {
        this.$('#g-user-action-menu>ul').prepend(jobs_userMenu({
            href: '#jobs/user/' + currentUser.id
        }));
    }
    return this;
});
