/**
 * This widget can be used to display a small loading animation.
 */
girder.views.LoadingAnimation = girder.View.extend({
    render: function () {
        this.$el.html(girder.templates.loadingAnimation());
        return this;
    }
});
