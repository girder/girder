import HeaderUserView from '@girder/core/views/layout/HeaderUserView';
import { getCurrentUser } from '@girder/core/auth';
import { wrap } from '@girder/core/utilities/PluginUtils';

import HeaderUserViewMenuTemplate from '../templates/headerUserViewMenu.pug';

/**
 * Add an entry to the user dropdown menu to navigate to user's job list view.
 */
wrap(HeaderUserView, 'render', function (render) {
    render.call(this);

    var currentUser = getCurrentUser();
    if (currentUser) {
        this.$('#g-user-action-menu>ul').prepend(HeaderUserViewMenuTemplate({
            href: '#jobs/user/' + currentUser.id
        }));
    }
    return this;
});
