/**
 * This view shows a list of global navigation links that should be
 * displayed at all times.
 */
girder.views.LayoutGlobalNavView = girder.View.extend({
    events: {
        'click .g-nav-link': function (event) {
            var link = $(event.currentTarget);

            girder.router.navigate(link.attr('g-target'), {trigger: true});

            // Must call this after calling navigateTo, since that
            // deactivates all global nav links.
            link.parent().addClass('g-active');
        }
    },

    initialize: function () {
        girder.events.on('g:highlightItem', this.selectForView, this);
        girder.events.on('g:login', this.render, this);
    },

    render: function () {
        var navItems = [{
            'name': 'Collections',
            'icon': 'icon-sitemap',
            'target': 'collections'
        }, {
            'name': 'Users',
            'icon': 'icon-user',
            'target': 'users'
        }, {
            'name': 'Groups',
            'icon': 'icon-users',
            'target': 'groups'
        }];
        if (girder.currentUser && girder.currentUser.get('admin')) {
            navItems.push({
                'name': 'Admin console',
                'icon': 'icon-wrench',
                'target': 'admin'
            });
        }
        this.$el.html(jade.templates.layoutGlobalNav({
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
