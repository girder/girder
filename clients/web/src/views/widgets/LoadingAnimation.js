/**
 * This widget can be used to display a small loading animation.
 */
girder.views.LoadingAnimation = Backbone.View.extend({
    render: function () {
        this.$el.html(jade.templates.loadingAnimation());
        return this;
    }
});
