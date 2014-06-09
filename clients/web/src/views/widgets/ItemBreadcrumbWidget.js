/**
 * Renders the a breadcrumb for the item page
 */
girder.views.ItemBreadcrumbWidget = girder.View.extend({
    events: {
        'click a.g-item-breadcrumb-link': function (event) {
            var link = $(event.currentTarget);
            girder.router.navigate(link.data('type') + '/' + link.data('id'),
                                   {trigger: true});
        }
    },

    initialize: function (settings) {
        this.parentChain = settings.parentChain;
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.itemBreadcrumb({
            parentChain: this.parentChain
        }));
    }
});
