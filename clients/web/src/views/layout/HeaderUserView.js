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

        'click a.g-logout': girder.logout,

        'click a.g-my-folders': function () {
            girder.router.navigate('user/' + girder.currentUser.get('_id'), {trigger: true});
        },

        'click a.g-my-settings': function () {
            girder.router.navigate('useraccount/' + girder.currentUser.get('_id') +
                                   '/info', {trigger: true});
        }
    },

    initialize: function () {
        girder.events.on('g:login', this.render, this);
        girder.events.on('g:login-changed', this.render, this);
    },

    render: function () {
        this.$el.html(girder.templates.layoutHeaderUser({
            user: girder.currentUser
        }));
        return this;
    }
});
