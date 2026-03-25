import HeaderUserViewMenuTemplate from '../templates/headerUserViewMenu.pug';

const HeaderUserView = girder.views.layout.HeaderUserView;
const { getCurrentUser } = girder.auth;
const { wrap } = girder.utilities.PluginUtils;

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
