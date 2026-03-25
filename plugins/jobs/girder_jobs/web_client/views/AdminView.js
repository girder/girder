import adminViewMenuItemTemplate from '../templates/adminViewMenuItem.pug';

const { wrap } = girder.utilities.PluginUtils;
const AdminView = girder.views.body.AdminView;

/**
 * Add an entry to the AdminView
 */
wrap(AdminView, 'render', function (render) {
    render.call(this);

    this.$('ul.g-admin-options').append(adminViewMenuItemTemplate());

    return this;
});
