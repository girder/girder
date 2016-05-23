import Auth                     from 'girder/auth';
import Events                   from 'girder/events';
import LayoutHeaderUserTemplate from 'girder/templates/layout/layoutHeaderUser.jade';
import router                   from 'girder/router';
import View                     from 'girder/view';

import 'bootstrap/js/dropdown';

/**
 * This view shows the user menu, or register/sign in links if the user is
 * not logged in.
 */
export var LayoutHeaderUserView = View.extend({
    events: {
        'click a.g-login': function () {
            Events.trigger('g:loginUi');
        },

        'click a.g-register': function () {
            Events.trigger('g:registerUi');
        },

        'click a.g-logout': Auth.logout,

        'click a.g-my-folders': function () {
            router.navigate('user/' + Auth.getCurrentUser().get('_id'), {trigger: true});
        },

        'click a.g-my-settings': function () {
            router.navigate('useraccount/' + Auth.getCurrentUser().get('_id') +
                                   '/info', {trigger: true});
        }
    },

    initialize: function () {
        Events.on('g:login', this.render, this);
        Events.on('g:login-changed', this.render, this);
        Events.on('g:logout', this.render, this);
    },

    render: function () {
        this.$el.html(LayoutHeaderUserTemplate({
            user: Auth.getCurrentUser()
        }));
        return this;
    }
});
