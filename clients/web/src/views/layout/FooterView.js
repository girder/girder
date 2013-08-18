/**
 * This view shows the footer in the layout.
 */
girder.views.LayoutFooterView = Backbone.View.extend({
    events: {
    },

    render: function () {
        this.$el.html(jade.templates.layoutFooter());
        return this;
    }
});
