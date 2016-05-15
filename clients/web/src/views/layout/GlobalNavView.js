var girder   = require('girder/init');
var Auth     = require('girder/auth');
var Events   = require('girder/events');
var Backbone = require('backbone');
var View     = require('girder/view');

/**
 * This view shows a list of global navigation links that should be
 * displayed at all times.
 */
var LayoutGlobalNavView = View.extend({
    events: {
        'click .g-nav-link': function (event) {
            event.preventDefault(); // so we can keep the href

            var link = $(event.currentTarget);

            girder.router.navigate(link.attr('g-target'), {trigger: true});

            // Must call this after calling navigateTo, since that
            // deactivates all global nav links.
            link.parent().addClass('g-active');
        }
    },

    initialize: function (settings) {
        Events.on('g:highlightItem', this.selectForView, this);
        Events.on('g:login', this.render, this);
        Events.on('g:logout', this.render, this);
        Events.on('g:login-changed', this.render, this);

        settings = settings || {};
        if (settings.navItems) {
            this.navItems = settings.navItems;
        } else {
            this.defaultNavItems = [{
                name: 'Collections',
                icon: 'icon-sitemap',
                target: 'collections'
            }, {
                name: 'Users',
                icon: 'icon-user',
                target: 'users'
            }, {
                name: 'Groups',
                icon: 'icon-users',
                target: 'groups'
            }];
        }
    },

    render: function () {
        var navItems;
        if (this.navItems) {
            navItems = this.navItems;
        } else {
            navItems = this.defaultNavItems;
            if (Auth.getCurrentUser() && Auth.getCurrentUser().get('admin')) {
                // copy navItems so that this.defaultNavItems is unchanged
                navItems = navItems.slice();
                navItems.push({
                    name: 'Admin console',
                    icon: 'icon-wrench',
                    target: 'admin'
                });
            }
        }
        this.$el.html(girder.templates.layoutGlobalNav({
            navItems: navItems
        }));

        if (Backbone.history.fragment) {
            this.$('[g-target="' + Backbone.history.fragment + '"]')
                .parent().addClass('g-active');
        }

        return this;
    },

    /**
     * Highlight the item with the given target attribute, which is the name
     * of the view it navigates to.
     */
    selectForView: function (viewName) {
        this.deactivateAll();
        this.$('[g-name="' + viewName.slice(0, -4) + '"]').parent().addClass('g-active');
    },

    deactivateAll: function () {
        this.$('.g-global-nav-li').removeClass('g-active');
    }
});

module.exports = LayoutGlobalNavView;
