var $                 = require('jquery');
var girder            = require('girder/init');
var Auth              = require('girder/auth');
var Events            = require('girder/events');
var UserCollection    = require('girder/collections/UserCollection');
var UserModel         = require('girder/models/UserModel');
var View              = require('girder/view');
var PaginateWidget    = require('girder/views/widgets/PaginateWidget');
var SearchFieldWidget = require('girder/views/widgets/SearchFieldWidget');
var RegisterView      = require('girder/views/layout/RegisterView');
var MiscFunctions     = require('girder/utilities/MiscFunctions');

var UserListTemplate = require('girder/templates/body/userList.jade');

/**
 * This view lists users.
 */
var UsersView = View.extend({
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
        MiscFunctions.cancelRestRequests('fetch');
        this.collection = new UserCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Search users...',
            types: ['user'],
            modes: 'prefix',
            parentView: this
        }).on('g:resultClicked', this._gotoUser, this);

        this.register = settings.dialog === 'register' && Auth.getCurrentUser() &&
                        Auth.getCurrentUser().get('admin');
    },

    render: function () {
        this.$el.html(UserListTemplate({
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
        var user = new UserModel();
        user.set('_id', result.id).on('g:fetched', function () {
            girder.router.navigate('user/' + user.get('_id'), {trigger: true});
        }, this).fetch();
    },

    createUserDialog: function () {
        var container = $('#g-dialog-container');

        new RegisterView({
            el: container,
            parentView: this
        }).on('g:userCreated', function (info) {
            girder.router.navigate('user/' + info.user.id, {trigger: true});
        }, this).render();
    }
});

module.exports = UsersView;

girder.router.route('users', 'users', function (params) {
    Events.trigger('g:navigateTo', UsersView, params || {});
    Events.trigger('g:highlightItem', 'UsersView');
});
