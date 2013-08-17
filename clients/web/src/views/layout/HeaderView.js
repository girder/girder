/**
 * This view shows the header in the layout.
 */
girder.views.LayoutHeaderView = Backbone.View.extend({
    events: {
    },

    render: function () {
        this.$el.html(jade.templates.layoutHeader());
        return this;
    }
});
