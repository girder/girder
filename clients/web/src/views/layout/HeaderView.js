/**
 * This view shows the header in the layout.
 */
girder.views.LayoutHeaderView = Backbone.View.extend({
    events: {
        // TODO quick search form handling
    },

    render: function () {
        this.$el.html(jade.templates.layoutHeader());

        new girder.views.LayoutHeaderUserView({
            el: this.$('.g-current-user-wrapper')
        }).render();

        return this;
    }
});
