/**
 * This view lists users.
 */
girder.views.UsersView = Backbone.View.extend({
    events: {
        'click a.g-user-link': function (event) {
            "use strict" ;
            var cid = $(event.currentTarget).attr('g-user-cid');
            var params = {
                user: this.collection.get(cid)
            };
            girder.events.trigger('g:navigateTo', girder.views.UserView, params);
        }
    },

    initialize: function () {
        "use strict";
        this.collection = new girder.collections.UserCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        "use strict";
        this.$el.html(jade.templates.userList({
            users: this.collection.models,
            girder: girder
        }));
        return this;
    }
});
