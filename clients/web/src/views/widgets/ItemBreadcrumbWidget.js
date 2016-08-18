/**
 * Renders the a breadcrumb for the item page
 */
girder.views.ItemBreadcrumbWidget = girder.View.extend({
    initialize: function (settings) {
        this.parentChain = settings.parentChain;
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.itemBreadcrumb({
            parentChain: this.parentChain
        }));

        this.$('.g-hierarchy-level-up').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });
    }
});
