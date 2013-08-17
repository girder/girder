/**
 * This view shows a list of global navigation links that should be
 * displayed at all times.
 */
girder.views.LayoutGlobalNavView = Backbone.View.extend({
    events: {
        'click .g-nav-link': 'navLinkClicked'
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
        }, {
            'name': 'Search',
            'icon': 'icon-search',
            'target': 'search'
        }];
        this.$el.html(jade.templates.layoutGlobalNav({
            navItems: navItems
        }));

        return this;
    },

    navLinkClicked: function (event) {
        var link = $(event.currentTarget);

        this.$('.g-global-nav-li').removeClass('g-active');
        link.parent().addClass('g-active');

        this.trigger('navigateTo', link.attr('g-target'));
    }
});
