import { wrap } from 'girder/utilities/PluginUtils';
import { getCurrentUser } from 'girder/auth';

/**
 * Add an entry to the user dropdown menu to navigate to user's job list view.
 */
import HeaderUserView from 'girder/views/layout/HeaderUserView';
import userMenuTemplate from './templates/userMenu.jade';
wrap(HeaderUserView, 'render', function (render) {
    render.call(this);

    var currentUser = getCurrentUser();
    if (currentUser) {
        this.$('#g-user-action-menu>ul').prepend(userMenuTemplate({
            href: '#jobs/user/' + currentUser.id
        }));
    }
    return this;
});
