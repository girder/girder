/**
 * This view lists users.
 */
girder.views.UsersView = girder.View.extend({
    events: {
        'click a.g-user-link': function (event) {
            var cid = $(event.currentTarget).attr('g-user-cid');
            girder.router.navigate('user/' + this.collection.get(cid).id, {trigger: true});
        },
        'submit .g-user-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function () {
        girder.cancelRestRequests('fetch');
        this.collection = new girder.collections.UserCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = new girder.views.PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = new girder.views.SearchFieldWidget({
            placeholder: 'Search users...',
            types: ['user'],
            modes: 'prefix',
            parentView: this
        }).on('g:resultClicked', this._gotoUser, this);
    },

    render: function () {
        this.$el.html(girder.templates.userList({
            users: this.collection.models,
            girder: girder
        }));

        this.paginateWidget.setElement(this.$('.g-user-pagination')).render();
        this.searchWidget.setElement(this.$('.g-users-search-container')).render();

        return this;
    },

    /**
     * When the user clicks a search result user, this helper method
     * will navigate them to the view for that specific user.
     */
    _gotoUser: function (result) {
        var user = new girder.models.UserModel();
        user.set('_id', result.id).on('g:fetched', function () {
            girder.router.navigate('user/' + user.get('_id'), {trigger: true});
        }, this).fetch();
    }
});

girder.router.route('users', 'users', function () {
    girder.events.trigger('g:navigateTo', girder.views.UsersView);
    girder.events.trigger('g:highlightItem', 'UsersView');
});
