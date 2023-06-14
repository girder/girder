/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import eventStream from '@girder/core/utilities/EventStream';
import { getCurrentUser, setCurrentUser } from '@girder/core/auth';
import { restRequest } from '@girder/core/rest';

/**
 * Admin
 */
import AdminView from '@girder/core/views/body/AdminView';
router.route('admin', 'admin', function () {
    events.trigger('g:navigateTo', AdminView);
});

/**
 * Assetstores
 */
import AssetstoresView from '@girder/core/views/body/AssetstoresView';
router.route('assetstores', 'assetstores', function (params) {
    events.trigger('g:navigateTo', AssetstoresView, {
        assetstoreEdit: params.dialog === 'assetstoreedit' ? params.dialogid : false
    });
});
router.route('assetstore/:id/import', 'assetstoreImport', function (assetstoreId) {
    AssetstoresView.import(assetstoreId);
});

/**
 * Collections
 */
import CollectionsView from '@girder/core/views/body/CollectionsView';
router.route('collections', 'collections', function (params) {
    events.trigger('g:navigateTo', CollectionsView, params || {});
    events.trigger('g:highlightItem', 'CollectionsView');
});

/**
 * Collection
 */
import CollectionView from '@girder/core/views/body/CollectionView';
router.route('collection/:id', 'collectionAccess', function (cid, params) {
    CollectionView.fetchAndInit(cid, {
        access: params.dialog === 'access',
        edit: params.dialog === 'edit',
        folderCreate: params.dialog === 'foldercreate',
        dialog: params.dialog
    });
});
router.route('collection/:id/folder/:id', 'collectionFolder', function (cid, folderId, params) {
    CollectionView.fetchAndInit(cid, {
        folderId: folderId,
        upload: params.dialog === 'upload',
        access: params.dialog === 'access',
        edit: params.dialog === 'edit',
        folderAccess: params.dialog === 'folderaccess',
        folderCreate: params.dialog === 'foldercreate',
        folderEdit: params.dialog === 'folderedit',
        itemCreate: params.dialog === 'itemcreate'
    });
});

/**
 * Folder
 */
import FolderView from '@girder/core/views/body/FolderView';
router.route('folder/:id', 'folder', function (id, params) {
    FolderView.fetchAndInit(id, {
        upload: params.dialog === 'upload',
        folderAccess: params.dialog === 'folderaccess',
        folderCreate: params.dialog === 'foldercreate',
        folderEdit: params.dialog === 'folderedit',
        itemCreate: params.dialog === 'itemcreate'
    });
});

/**
 * FrontPage
 */
import FrontPageView from '@girder/core/views/body/FrontPageView';
router.route('', 'index', function () {
    events.trigger('g:navigateTo', FrontPageView);
});

/**
 * Groups
 */
import GroupsView from '@girder/core/views/body/GroupsView';
router.route('groups', 'groups', function (params) {
    events.trigger('g:navigateTo', GroupsView, params || {});
    events.trigger('g:highlightItem', 'GroupsView');
});

/**
 * Group
 */
import GroupView from '@girder/core/views/body/GroupView';
router.route('group/:id', 'groupView', function (groupId, params) {
    GroupView.fetchAndInit(groupId, {
        edit: params.dialog === 'edit'
    });
});
router.route('group/:id/:tab', 'groupView', function (groupId, tab, params) {
    GroupView.fetchAndInit(groupId, {
        edit: params.dialog === 'edit',
        tab: tab
    });
});

/**
 * Item
 */
import ItemView from '@girder/core/views/body/ItemView';
router.route('item/:id', 'item', function (itemId, params) {
    ItemView.fetchAndInit(itemId, {
        edit: params.dialog === 'itemedit',
        fileEdit: params.dialog === 'fileedit' ? params.dialogid : false,
        upload: params.dialog === 'upload' ? params.dialogid : false
    });
});

/**
 * Plugins
 */
import PluginsView from '@girder/core/views/body/PluginsView';
import UsersView from '@girder/core/views/body/UsersView';
router.route('plugins', 'plugins', function () {
    events.trigger('g:navigateTo', PluginsView);
});

/**
 * SystemConfiguration
 */
import SystemConfigurationView from '@girder/core/views/body/SystemConfigurationView';
router.route('settings', 'settings', function () {
    events.trigger('g:navigateTo', SystemConfigurationView);
});

/**
 * UserAccount
 */
import UserAccountView from '@girder/core/views/body/UserAccountView';
import UserModel from '@girder/core/models/UserModel';
router.route('useraccount/:id/:tab', 'accountTab', function (id, tab) {
    UserAccountView.fetchAndInit(id, tab);
});
router.route('useraccount/:id/token/:token', 'accountToken', function (id, token) {
    UserModel.fromTemporaryToken(id, token)
        .done(() => {
            events.trigger('g:navigateTo', UserAccountView, {
                user: getCurrentUser(),
                tab: 'password',
                temporary: token
            });
        }).fail(() => {
            router.navigate('', { trigger: true });
        });
});

router.route('useraccount/:id/verification/:token', 'accountVerify', function (id, token) {
    restRequest({
        url: `user/${id}/verification`,
        method: 'PUT',
        data: { token: token },
        error: null
    }).done((resp) => {
        if (resp.authToken) {
            resp.user.token = resp.authToken.token;
            eventStream.close();
            setCurrentUser(new UserModel(resp.user));
            eventStream.open();
            events.trigger('g:login-changed');
        }
        events.trigger('g:navigateTo', FrontPageView);
        events.trigger('g:alert', {
            icon: 'ok',
            text: 'Email verified.',
            type: 'success',
            timeout: 4000
        });
    }).fail(() => {
        events.trigger('g:navigateTo', FrontPageView);
        events.trigger('g:alert', {
            icon: 'cancel',
            text: 'Could not verify email.',
            type: 'danger',
            timeout: 4000
        });
    });
});

/**
 * Users
 */
router.route('users', 'users', function (params) {
    events.trigger('g:navigateTo', UsersView, params || {});
    events.trigger('g:highlightItem', 'UsersView');
});

/**
 * User
 */
import UserView from '@girder/core/views/body/UserView';
router.route('user/:id', 'user', function (userId, params) {
    UserView.fetchAndInit(userId, {
        folderCreate: params.dialog === 'foldercreate',
        dialog: params.dialog
    });
});
router.route('user/:id/folder/:id', 'userFolder', function (userId, folderId, params) {
    UserView.fetchAndInit(userId, {
        folderId: folderId,
        upload: params.dialog === 'upload',
        folderAccess: params.dialog === 'folderaccess',
        folderCreate: params.dialog === 'foldercreate',
        folderEdit: params.dialog === 'folderedit',
        itemCreate: params.dialog === 'itemcreate'
    });
});

/**
 * SearchResults
 */
import SearchResultsView from '@girder/core/views/body/SearchResultsView';
router.route('search/results', 'SearchResults', function (params) {
    events.trigger('g:navigateTo', SearchResultsView, {
        query: params.query,
        mode: params.mode
    });
});
