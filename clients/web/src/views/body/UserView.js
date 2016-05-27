import _ from 'underscore';

import { AccessType } from 'girder/constants';
import { events } from 'girder/events';
import FolderModel from 'girder/models/FolderModel';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import { confirm } from 'girder/utilities/MiscFunctions';
import { cancelRestRequests } from 'girder/rest';
import router from 'girder/router';
import UserModel from 'girder/models/UserModel';
import UserPageTemplate from 'girder/templates/body/userPage.jade';
import UsersView from 'girder/views/body/UsersView';
import View from 'girder/view';

import 'bootstrap/js/dropdown';

/**
 * This view shows a single user's page.
 */
var UserView = View.extend({
    events: {
        'click a.g-edit-user': function () {
            var editUrl = 'useraccount/' + this.model.get('_id') + '/info';
            router.navigate(editUrl, {trigger: true});
        },

        'click a.g-delete-user': function () {
            confirm({
                text: 'Are you sure you want to delete the user <b>' +
                      this.model.escape('login') + '</b>?',
                yesText: 'Delete',
                escapedHtml: true,
                confirmCallback: _.bind(function () {
                    this.model.destroy().on('g:deleted', function () {
                        router.navigate('users', {trigger: true});
                    });
                }, this)
            });
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.folderId = settings.folderId || null;
        this.upload = settings.upload || false;
        this.folderAccess = settings.folderAccess || false;
        this.folderCreate = settings.folderCreate || false;
        this.folderEdit = settings.folderEdit || false;
        this.itemCreate = settings.itemCreate || false;

        if (settings.user) {
            this.model = settings.user;

            if (settings.folderId) {
                this.folder = new FolderModel();
                this.folder.set({
                    _id: settings.folderId
                }).on('g:fetched', function () {
                    this._createHierarchyWidget();
                    this.render();
                }, this).on('g:error', function () {
                    this.folder = null;
                    this._createHierarchyWidget();

                    this.render();
                }, this).fetch();
            } else {
                this._createHierarchyWidget();
                this.render();
            }
        } else if (settings.id) {
            this.model = new UserModel();
            this.model.set('_id', settings.id);

            this.model.on('g:fetched', function () {
                this._createHierarchyWidget();
                this.render();
            }, this).fetch();
        }
    },

    _createHierarchyWidget: function () {
        this.hierarchyWidget = new HierarchyWidget({
            parentModel: this.folder || this.model,
            upload: this.upload,
            folderAccess: this.folderAccess,
            folderEdit: this.folderEdit,
            folderCreate: this.folderCreate,
            itemCreate: this.itemCreate,
            parentView: this
        });
    },

    render: function () {
        this.$el.html(UserPageTemplate({
            user: this.model,
            AccessType: AccessType
        }));

        this.hierarchyWidget.setElement(this.$('.g-user-hierarchy-container')).render();

        this.upload = false;
        this.folderAccess = false;
        this.folderEdit = false;
        this.folderCreate = false;
        this.itemCreate = false;

        return this;
    }
});

/**
 * Helper function for fetching the user and rendering the view with
 * an arbitrary set of extra parameters.
 */
var _fetchAndInit = function (userId, params) {
    var user = new UserModel();
    user.set({
        _id: userId
    }).on('g:fetched', function () {
        events.trigger('g:navigateTo', UserView, _.extend({
            user: user
        }, params || {}));
    }, this).on('g:error', function () {
        events.trigger('g:navigateTo', UsersView);
    }, this).fetch();
};

router.route('user/:id', 'user', function (userId, params) {
    _fetchAndInit(userId, {
        folderCreate: params.dialog === 'foldercreate',
        dialog: params.dialog
    });
});

router.route('user/:id/folder/:id', 'userFolder', function (userId, folderId, params) {
    _fetchAndInit(userId, {
        folderId: folderId,
        upload: params.dialog === 'upload',
        folderAccess: params.dialog === 'folderaccess',
        folderCreate: params.dialog === 'foldercreate',
        folderEdit: params.dialog === 'folderedit',
        itemCreate: params.dialog === 'itemcreate'
    });
});

export default UserView;
