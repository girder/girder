import View from 'girder/views/View';
import events from 'girder/events';
import { logout, getCurrentUser } from 'girder/auth';

import LayoutHeaderUserTemplate from 'girder/templates/layout/layoutHeaderUser.pug';

import 'girder/stylesheets/layout/headerUser.styl';

import 'bootstrap/js/dropdown';

/**
 * This view shows the user menu, or register/sign in links if the user is
 * not logged in.
 */
var LayoutHeaderUserView = View.extend({
    events: {
        'click a.g-logout': logout
    },

    initialize: function () {
        events.on('g:login', this.render, this);
        events.on('g:login-changed', this.render, this);
        events.on('g:logout', this.render, this);
    },

    render: function () {
        this.$el.html(LayoutHeaderUserTemplate({
            user: getCurrentUser()
        }));
        return this;
    }
});

export default LayoutHeaderUserView;
