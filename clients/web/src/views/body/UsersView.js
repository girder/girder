/**
 * This view lists users.
 */
girder.views.UsersView = girder.View.extend({
    events: {
        'click a.g-user-link': function (event) {
            var cid = $(event.currentTarget).attr('g-user-cid');
            girder.router.navigate('user/' + this.collection.get(cid).id, {trigger: true});
        },
        'click button.g-user-create-button': 'createUserDialog',
        'submit .g-user-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function (settings) {
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

        this.register = settings.dialog === 'register' && girder.currentUser &&
                        girder.currentUser.get('admin');
    },

    render: function () {
        this.$el.html(girder.templates.userList({
            users: this.collection.toArray(),
            girder: girder
        }));

        this.paginateWidget.setElement(this.$('.g-user-pagination')).render();
        this.searchWidget.setElement(this.$('.g-users-search-container')).render();

        if (this.register) {
            this.createUserDialog();
        }

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
    },

    createUserDialog: function () {
        var container = $('#g-dialog-container');

        new girder.views.RegisterView({
            el: container,
            parentView: this
        }).on('g:userCreated', function (info) {
            girder.router.navigate('user/' + info.user.id, {trigger: true});
        }, this).render();
    }
});

girder.router.route('users', 'users', function (params) {
    girder.events.trigger('g:navigateTo', girder.views.UsersView, params || {});
    girder.events.trigger('g:highlightItem', 'UsersView');
});
