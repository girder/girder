/**
 * This view shows a list of global navigation links that should be
 * displayed at all times.
 */
girder.views.LayoutGlobalNavView = Backbone.View.extend({
    events: {
        'click .g-nav-link': function (event) {
            var link = $(event.currentTarget);

            girder.events.trigger('g:navigateTo',
                                  girder.views[link.attr('g-target')]);

            // Must call this after calling navigateTo, since that
            // deactivates all global nav links.
            link.parent().addClass('g-active');
        }
    },

    render: function () {
        var navItems = [{
            'name': 'Collections',
            'icon': 'icon-sitemap',
            'target': 'CollectionsView'
        }, {
            'name': 'Users',
            'icon': 'icon-user',
            'target': 'UsersView'
        }, {
            'name': 'Groups',
            'icon': 'icon-users',
            'target': 'GroupsView'
        }, {
            'name': 'Search',
            'icon': 'icon-search',
            'target': 'SearchView'
        }];
        this.$el.html(jade.templates.layoutGlobalNav({
            navItems: navItems
        }));

        return this;
    },

    deactivateAll: function () {
        this.$('.g-global-nav-li').removeClass('g-active');
    }
});
