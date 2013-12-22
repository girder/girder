/**
 * This view lists users.
 */
girder.views.UsersView = Backbone.View.extend({
    events: {
        'click a.g-user-link': function (event) {
            var cid = $(event.currentTarget).attr('g-user-cid');
            var params = {
                user: this.collection.get(cid)
            };
            girder.events.trigger('g:navigateTo', girder.views.UserView, params);
        },
        'submit .g-user-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function () {
        this.collection = new girder.collections.UserCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        this.$el.html(jade.templates.userList({
            users: this.collection.models,
            girder: girder
        }));

        new girder.views.PaginateWidget({
            el: this.$('.g-user-pagination'),
            collection: this.collection
        }).render();

        new girder.views.SearchFieldWidget({
            el: this.$('.g-users-search-container'),
            placeholder: 'Search users...',
            types: ['user']
        }).off().on('g:resultClicked', this._gotoUser, this).render();

        girder.router.navigate('users');

        return this;
    },

    /**
     * When the user clicks a search result user, this helper method
     * will navigate them to the view for that specific user.
     */
    _gotoUser: function (result) {
        var user = new girder.models.UserModel();
        user.set('_id', result.id).on('g:fetched', function () {
            girder.events.trigger('g:navigateTo', girder.views.UserView, {
                user: user
            });
        }, this).fetch();
    }
});

girder.router.route('users', 'users', function () {
    girder.events.trigger('g:navigateTo', girder.views.UsersView);
    girder.events.trigger('g:highlightItem', 'UsersView');
});
