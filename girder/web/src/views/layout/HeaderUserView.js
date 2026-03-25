import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { logout, getCurrentUser } from '@girder/core/auth';

import LayoutHeaderUserTemplate from '@girder/core/templates/layout/layoutHeaderUser.pug';

import '@girder/core/stylesheets/layout/headerUser.styl';

import 'bootstrap/js/dropdown';

/**
 * This view shows the user menu, or register/sign in links if the user is
 * not logged in.
 */
var LayoutHeaderUserView = View.extend({
    events: {
        'click a.g-login': function () {
            events.trigger('g:loginUi');
        },

        'click a.g-register': function () {
            events.trigger('g:registerUi');
        },

        'click a.g-logout': logout
    },

    initialize: function (settings) {
        this.registrationPolicy = settings.registrationPolicy;

        events.on('g:login', this.render, this);
        events.on('g:login-changed', this.render, this);
        events.on('g:logout', this.render, this);
    },

    render: function () {
        this.$el.html(LayoutHeaderUserTemplate({
            user: getCurrentUser(),
            registrationPolicy: this.registrationPolicy
        }));
        return this;
    }
});

export default LayoutHeaderUserView;
