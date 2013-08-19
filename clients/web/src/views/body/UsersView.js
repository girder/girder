/**
 * This view lists users.
 */
girder.views.UsersView = Backbone.View.extend({
    events: {
    },

    initialize: function () {
        // TODO fetch user list, render when done.
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.usersPage());
        return this;
    }
});
