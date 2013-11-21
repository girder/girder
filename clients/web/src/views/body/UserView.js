/**
 * This view shows a single user's page.
 */
girder.views.UserView = Backbone.View.extend({
    events: {
    },

    initialize: function (settings) {
        // If user model is already passed, there is no need to fetch.
        if (settings.user) {
            this.model = settings.user;
            this.render();
        }
        else {
            console.error('Implement fetch then render user');
        }

        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.userChanged, this);
    },

    render: function () {
        this.$el.html(jade.templates.userPage({
            user: this.model
        }));

        this.hierarchyWidget = new girder.views.HierarchyWidget({
            parentType: 'user',
            parentModel: this.model,
            el: this.$('.g-user-hierarchy-container')
        });

        girder.router.navigate('user/' + this.model.get('_id'));

        return this;
    },

    userChanged: function () {
        // When the user changes, we should refresh the model to update the
        // _accessLevel attribute on the viewed user, then re-render the page.
        this.model.off('g:fetched').on('g:fetched', function () {
            this.render();
        }, this).on('g:error', function () {
            // Current user no longer has read access to this user, so we
            // send them back to the user list page.
            girder.events.trigger('g:navigateTo', girder.views.UsersView);
        }, this).fetch();
    }
});

girder.router.route('user/:id', 'user', function (id) {
    // Fetch the user by id, then render the view.
    var user = new girder.models.UserModel();
    user.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.UserView, {
            user: user
        }, user);
    }, this).on('g:error', function () {
        girder.events.trigger('g:navigateTo', girder.views.UsersView);
    }, this).fetch();
});
