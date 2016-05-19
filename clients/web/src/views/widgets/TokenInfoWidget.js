/**
 * This view shows a dialog containing current user's token.
 */
girder.views.TokenInfoWidget = girder.View.extend({
    initialize: function () {
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.tokenInfoDialog({
            currentToken: girder.currentToken
        })).girderModal(this);
    }
});
