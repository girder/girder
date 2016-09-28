import _ from 'underscore';

import FolderModel from 'girder/models/FolderModel';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import router from 'girder/router';
import UserModel from 'girder/models/UserModel';
import UsersView from 'girder/views/body/UsersView';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { cancelRestRequests } from 'girder/rest';
import { confirm } from 'girder/dialog';
import events from 'girder/events';

import UserPageTemplate from 'girder/templates/body/userPage.pug';

import 'girder/stylesheets/body/userPage.styl';

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
                    this.model.on('g:deleted', function () {
                        router.navigate('users', {trigger: true});
                    }).destroy();
                }, this)
            });
        },

        'click a.g-approve-user': function () {
            this._setAndSave(
                {status: 'enabled'}, 'Approved user account.');
        },

        'click a.g-disable-user': function () {
            this._setAndSave(
                {status: 'disabled'}, 'Disabled user account.');
        },

        'click a.g-enable-user': function () {
            this._setAndSave(
                {status: 'enabled'}, 'Enabled user account.');
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
    },

    _setAndSave: function (data, message) {
        this.model.set(data);
        this.model.off('g:saved').on('g:saved', function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: message,
                type: 'success',
                timeout: 4000
            });
            this.render();
        }, this).off('g:error').on('g:error', function (err) {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: err.responseJSON.message,
                type: 'danger'
            });
        }).save();
    }
}, {
    /**
     * Helper function for fetching the user and rendering the view with
     * an arbitrary set of extra parameters.
     */
    fetchAndInit: function (userId, params) {
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
    }
});

export default UserView;
