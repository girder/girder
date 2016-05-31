import _ from 'underscore';

import router from 'girder/router';
import { events } from 'girder/events';
import { restRequest } from 'girder/rest';

/**
 * Admin
 */
import AdminView from 'girder/views/body/AdminView';
router.route('admin', 'admin', function () {
    events.trigger('g:navigateTo', AdminView);
});

/**
 * Assetstores
 */
import AssetstoresView from 'girder/views/body/AssetstoresView';
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
import CollectionsView from 'girder/views/body/CollectionsView';
router.route('collections', 'collections', function (params) {
    events.trigger('g:navigateTo', CollectionsView, params || {});
    events.trigger('g:highlightItem', 'CollectionsView');
});

/**
 * Collection
 */
import CollectionView from 'girder/views/body/CollectionView';
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
import FolderView from 'girder/views/body/FolderView';
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
import FrontPageView from 'girder/views/body/FrontPageView';
router.route('', 'index', function () {
    events.trigger('g:navigateTo', FrontPageView);
});

/**
 * Groups
 */
import GroupsView from 'girder/views/body/GroupsView';
router.route('groups', 'groups', function (params) {
    events.trigger('g:navigateTo', GroupsView, params || {});
    events.trigger('g:highlightItem', 'GroupsView');
});

/**
 * Group
 */
import GroupView from 'girder/views/body/GroupView';
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
import ItemView from 'girder/views/body/ItemView';
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
import PluginsView from 'girder/views/body/PluginsView';
router.route('plugins', 'plugins', function () {
    // Fetch the plugin list
    restRequest({
        path: 'system/plugins',
        type: 'GET'
    }).done(_.bind(function (resp) {
        events.trigger('g:navigateTo', PluginsView, resp);
    }, this)).error(_.bind(function () {
        events.trigger('g:navigateTo', UsersView);
    }, this));
});

/**
 * SystemConfiguration
 */
import SystemConfigurationView from 'girder/views/body/SystemConfigurationView';
router.route('settings', 'settings', function () {
    events.trigger('g:navigateTo', SystemConfigurationView);
});

/**
 * UserAccount
 */
import UserAccountView from 'girder/views/body/UserAccountView';
router.route('useraccount/:id/:tab', 'accountTab', function (id, tab) {
    UserAccountView.fetchAndInit(id, tab);
});
router.route('useraccount/:id/token/:token', 'accountToken', function (id, token) {
    UserAccountView.temporaryPassword(id, token);
});

/**
 * Users
 */
import UsersView from 'girder/views/body/UsersView';
router.route('users', 'users', function (params) {
    events.trigger('g:navigateTo', UsersView, params || {});
    events.trigger('g:highlightItem', 'UsersView');
});

/**
 * User
 */
import UserView from 'girder/views/body/UserView';
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
