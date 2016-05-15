var girder = require('girder/init');
var Auth   = require('girder/auth');
var Events = require('girder/events');
var View   = require('girder/view');

/**
 * This view shows the user menu, or register/sign in links if the user is
 * not logged in.
 */
var LayoutHeaderUserView = View.extend({
    events: {
        'click a.g-login': function () {
            Events.trigger('g:loginUi');
        },

        'click a.g-register': function () {
            Events.trigger('g:registerUi');
        },

        'click a.g-logout': Auth.logout,

        'click a.g-my-folders': function () {
            girder.router.navigate('user/' + Auth.getCurrentUser().get('_id'), {trigger: true});
        },

        'click a.g-my-settings': function () {
            girder.router.navigate('useraccount/' + Auth.getCurrentUser().get('_id') +
                                   '/info', {trigger: true});
        }
    },

    initialize: function () {
        Events.on('g:login', this.render, this);
        Events.on('g:login-changed', this.render, this);
        Events.on('g:logout', this.render, this);
    },

    render: function () {
        this.$el.html(girder.templates.layoutHeaderUser({
            user: Auth.getCurrentUser()
        }));
        return this;
    }
});

module.exports = LayoutHeaderUserView;
