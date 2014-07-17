/**
 * This view shows the footer in the layout.
 */
girder.views.LayoutFooterView = girder.View.extend({
    render: function () {
        this.$el.html(jade.templates.layoutFooter({
            apiRoot: girder.apiRoot
        }));
        return this;
    }
});
