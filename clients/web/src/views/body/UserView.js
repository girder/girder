/**
 * This view shows a single user's page.
 */
girder.views.UserView = Backbone.View.extend({
    events: {
    },

    initialize: function (settings) {
        "use strict";
        // If user model is already passed, there is no need to fetch.
        if (settings.user) {
            this.model = settings.user;
            this.render();
        }
    },

    render: function () {
        "use strict";
        /*this.$el.html(jade.templates.userList({
            users: this.collection.models,
            girder: girder
        }));*/
        this.$el.html('hello world');
        return this;
    }
});
