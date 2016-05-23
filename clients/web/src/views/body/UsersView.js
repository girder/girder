import $                 from 'jquery';

import Auth              from 'girder/auth';
import Events            from 'girder/events';
import { formatDate, formatSize, DATE_DAY } from 'girder/utilities/MiscFunctions';
import PaginateWidget    from 'girder/views/widgets/PaginateWidget';
import RegisterView      from 'girder/views/layout/RegisterView';
import Rest              from 'girder/rest';
import router            from 'girder/router';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import UserCollection    from 'girder/collections/UserCollection';
import UserListTemplate  from 'girder/templates/body/userList.jade';
import UserModel         from 'girder/models/UserModel';
import View              from 'girder/view';

/**
 * This view lists users.
 */
export var UsersView = View.extend({
    events: {
        'click a.g-user-link': function (event) {
            var cid = $(event.currentTarget).attr('g-user-cid');
            router.navigate('user/' + this.collection.get(cid).id, {trigger: true});
        },
        'click button.g-user-create-button': 'createUserDialog',
        'submit .g-user-search-form': function (event) {
            event.preventDefault();
        }
    },

    initialize: function (settings) {
        Rest.cancelRestRequests('fetch');
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
            Auth: Auth,
            formatDate: formatDate,
            formatSize: formatSize,
            DATE_DAY: DATE_DAY
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
            router.navigate('user/' + user.get('_id'), {trigger: true});
        }, this).fetch();
    },

    createUserDialog: function () {
        var container = $('#g-dialog-container');

        new RegisterView({
            el: container,
            parentView: this
        }).on('g:userCreated', function (info) {
            router.navigate('user/' + info.user.id, {trigger: true});
        }, this).render();
    }
});

router.route('users', 'users', function (params) {
    Events.trigger('g:navigateTo', UsersView, params || {});
    Events.trigger('g:highlightItem', 'UsersView');
});
