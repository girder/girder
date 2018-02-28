import $ from 'jquery';

import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import RegisterView from 'girder/views/layout/RegisterView';
import router from 'girder/router';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import SortCollectionWidget from 'girder/views/widgets/SortCollectionWidget';
import UserCollection from 'girder/collections/UserCollection';
import UserModel from 'girder/models/UserModel';
import View from 'girder/views/View';
import { cancelRestRequests } from 'girder/rest';
import { formatDate, formatShortDate, formatSize, DATE_DAY } from 'girder/misc';
import { getCurrentUser } from 'girder/auth';

import UserListTemplate from 'girder/templates/body/userList.pug';

import 'girder/stylesheets/body/userList.styl';

/**
 * This view lists users.
 */
var UsersView = View.extend({
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
        cancelRestRequests('fetch');
        this.collection = new UserCollection();

        const promiseArray = [];
        promiseArray.push(this.collection.fetch());

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.sortCollectionWidget = new SortCollectionWidget({
            collection: this.collection,
            parentView: this,
            fields: {
                lastName: 'Last Name',
                created: 'Creation Date',
                size: 'Used Space'
            }
        });

        this.searchWidget = new SearchFieldWidget({
            placeholder: 'Search users...',
            types: ['user'],
            modes: 'prefix',
            parentView: this
        }).on('g:resultClicked', this._gotoUser, this);

        if (getCurrentUser() && getCurrentUser().get('admin')) {
            const userCountPromise = UserCollection.getTotalCount()
                .done((count) => {
                    this.usersCount = count;
                });
            promiseArray.push(userCountPromise);
        }
        this.register = settings.dialog === 'register' && getCurrentUser() &&
                        getCurrentUser().get('admin');

        $.when(...promiseArray)
            .done(() => {
                this.listenTo(this.collection, 'g:changed', this.render);
                this.render();
            });
    },

    render: function () {
        this.$el.html(UserListTemplate({
            users: this.collection.toArray(),
            currentUser: getCurrentUser(),
            usersCount: this.usersCount,
            formatDate: formatDate,
            formatShortDate: formatShortDate,
            formatSize: formatSize,
            DATE_DAY: DATE_DAY
        }));

        const userList = this.paginateWidget.collection;
        if (userList.hasNextPage() || userList.hasPreviousPage()) {
            this.paginateWidget.setElement(this.$('.g-user-pagination')).render();
        }
        this.sortCollectionWidget.setElement(this.$('.g-user-sort')).render();
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

export default UsersView;
