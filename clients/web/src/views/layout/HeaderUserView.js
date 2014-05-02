/**
 * This view shows the user menu, or register/sign in links if the user is
 * not logged in.
 */
girder.views.LayoutHeaderUserView = girder.View.extend({
    events: {
        'click a.g-login': function () {
            girder.events.trigger('g:loginUi');
        },

        'click a.g-register': function () {
            girder.events.trigger('g:registerUi');
        },

        'click a.g-logout': function () {
            girder.restRequest({
                path: 'user/authentication',
                type: 'DELETE'
            }).done(_.bind(function () {
                girder.currentUser = null;
                girder.events.trigger('g:login');
            }, this));
        },

        'click a.g-my-folders': function () {
            girder.events.trigger('g:navigateTo', girder.views.UserView, {
                user: girder.currentUser
            });
        },

        'click a.g-my-settings': function () {
            girder.events.trigger('g:navigateTo', girder.views.UserSettingsView, {
                user: girder.currentUser
            });
        },

        'click a.g-admin': function () {
            girder.events.trigger('g:navigateTo', girder.views.AdminView);
        }
    },

    initialize: function () {
        girder.events.on('g:login', this.render, this);
    },

    render: function () {
        this.$el.html(jade.templates.layoutHeaderUser({
            user: girder.currentUser
        }));
        return this;
    }
});
