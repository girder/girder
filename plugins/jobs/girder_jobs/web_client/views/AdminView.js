import { wrap } from '@girder/core/utilities/PluginUtils';
import AdminView from '@girder/core/views/body/AdminView';

import adminViewMenuItemTemplate from '../templates/adminViewMenuItem.pug';

/**
 * Add an entry to the AdminView
 */
wrap(AdminView, 'render', function (render) {
    render.call(this);

    this.$('ul.g-admin-options').append(adminViewMenuItemTemplate());

    return this;
});
