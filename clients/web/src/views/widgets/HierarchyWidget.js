import $ from 'jquery';
import _ from 'underscore';

import * as allModels from 'girder/models';
import AccessWidget from 'girder/views/widgets/AccessWidget';
import CheckedMenuWidget from 'girder/views/widgets/CheckedMenuWidget';
import CollectionInfoWidget from 'girder/views/widgets/CollectionInfoWidget';
import EditCollectionWidget from 'girder/views/widgets/EditCollectionWidget';
import EditFolderWidget from 'girder/views/widgets/EditFolderWidget';
import EditItemWidget from 'girder/views/widgets/EditItemWidget';
import FolderInfoWidget from 'girder/views/widgets/FolderInfoWidget';
import FolderListWidget from 'girder/views/widgets/FolderListWidget';
import ItemListWidget from 'girder/views/widgets/ItemListWidget';
import ItemModel from 'girder/models/ItemModel';
import MetadataWidget from 'girder/views/widgets/MetadataWidget';
import router from 'girder/router';
import UploadWidget from 'girder/views/widgets/UploadWidget';
import View from 'girder/views/View';
import { AccessType } from 'girder/constants';
import { confirm, handleClose } from 'girder/dialog';
import events from 'girder/events';
import { getModelClassByName, renderMarkdown, formatCount, capitalize } from 'girder/misc';
import { restRequest, apiRoot } from 'girder/rest';

import HierarchyBreadcrumbTemplate from 'girder/templates/widgets/hierarchyBreadcrumb.pug';
import HierarchyWidgetTemplate from 'girder/templates/widgets/hierarchyWidget.pug';

import 'girder/stylesheets/widgets/hierarchyWidget.styl';

import 'bootstrap/js/dropdown';
import 'bootstrap/js/tooltip';

var pickedResources = null;

/**
 * Renders the breadcrumb list in the hierarchy widget.
 */
var HierarchyBreadcrumbView = View.extend({
    events: {
        'click a.g-breadcrumb-link': function (event) {
            var link = $(event.currentTarget);
            this.trigger('g:breadcrumbClicked', parseInt(link.attr('g-index'), 10));
        }
    },

    initialize: function (settings) {
        this.objects = settings.objects;
    },

    render: function () {
        // Clone the array so we don't alter the instance's copy
        var objects = this.objects.slice(0);

        // Pop off the last object, it refers to the currently viewed
        // object and should be the "active" class, and not a link.
        var active = objects.pop();

        var descriptionText = $(renderMarkdown(
            active.get('description') || '')).text();

        this.$el.html(HierarchyBreadcrumbTemplate({
            links: objects,
            current: active,
            descriptionText: descriptionText
        }));
    }
});

/**
 * This widget is used to navigate the data hierarchy of folders and items.
 */
var HierarchyWidget = View.extend({
    events: {
        'click a.g-create-subfolder': 'createFolderDialog',
        'click a.g-edit-folder': 'editFolderDialog',
        'click a.g-delete-folder': 'deleteFolderDialog',
        'click .g-folder-info-button': 'showInfoDialog',
        'click .g-collection-info-button': 'showInfoDialog',
        'click .g-description-preview': 'showInfoDialog',
        'click a.g-create-item': 'createItemDialog',
        'click .g-upload-here-button': 'uploadDialog',
        'click .g-edit-access': 'editAccess',
        'click .g-hierarchy-level-up': 'upOneLevel',
        'click a.g-download-checked': 'downloadChecked',
        'click a.g-pick-checked': 'pickChecked',
        'click a.g-move-picked': 'movePickedResources',
        'click a.g-copy-picked': 'copyPickedResources',
        'click a.g-clear-picked': 'clearPickedResources',
        'click a.g-delete-checked': 'deleteCheckedDialog',
        'click .g-list-checkbox': 'checkboxListener',
        'change .g-select-all': function (e) {
            this.folderListView.checkAll(e.currentTarget.checked);

            if (this.itemListView) {
                this.itemListView.checkAll(e.currentTarget.checked);
            }
        }
    },

    /**
     * This should be instantiated with the following settings:
     *   parentModel: The model representing the root node. Must be a User,
     *                 Collection, or Folder model.
     *   [showActions=true]: Whether to show the action bar.
     *   [showItems=true]: Whether to show items in the list (or just folders).
     *   [checkboxes=true]: Whether to show checkboxes next to each resource.
     *   [routing=true]: Whether the route should be updated by this widget.
     *   [appendPages=false]: Whether new pages should be appended instead of
     *                        replaced.
     *   [onItemClick]: A function that will be called when an item is clicked,
     *                  passed the Item model as its first argument and the
     *                  event as its second.
     */
    initialize: function (settings) {
        this.parentModel = settings.parentModel;
        this.upload = settings.upload;

        this._showActions = _.has(settings, 'showActions') ? settings.showActions : true;
        this._showItems = _.has(settings, 'showItems') ? settings.showItems : true;
        this._checkboxes = _.has(settings, 'checkboxes') ? settings.checkboxes : true;
        this._routing = _.has(settings, 'routing') ? settings.routing : true;
        this._appendPages = _.has(settings, 'appendPages') ? settings.appendPages : false;
        this._onItemClick = settings.onItemClick || function (item) {
            router.navigate('item/' + item.get('_id'), {trigger: true});
        };

        this.folderAccess = settings.folderAccess;
        this.folderCreate = settings.folderCreate;
        this.folderEdit = settings.folderEdit;
        this.itemCreate = settings.itemCreate;
        this.breadcrumbs = [this.parentModel];

        // Initialize the breadcrumb bar state
        this.breadcrumbView = new HierarchyBreadcrumbView({
            objects: this.breadcrumbs,
            parentView: this
        });
        this.breadcrumbView.on('g:breadcrumbClicked', function (idx) {
            this.breadcrumbs = this.breadcrumbs.slice(0, idx + 1);
            this.setCurrentModel(this.breadcrumbs[idx]);
            this._setRoute();
        }, this);

        this.checkedMenuWidget = new CheckedMenuWidget({
            pickedCount: this.getPickedCount(),
            pickedCopyAllowed: this.getPickedCopyAllowed(),
            pickedMoveAllowed: this.getPickedMoveAllowed(),
            pickedDesc: this.getPickedDescription(),
            parentView: this
        });

        this.folderListView = new FolderListWidget({
            parentType: this.parentModel.resourceName,
            parentId: this.parentModel.get('_id'),
            checkboxes: this._checkboxes,
            parentView: this
        });
        this.folderListView.on('g:folderClicked', function (folder) {
            this.descend(folder);

            if (this.uploadWidget) {
                this.uploadWidget.folder = folder;
            }
        }, this).off('g:checkboxesChanged')
                .on('g:checkboxesChanged', this.updateChecked, this)
                .off('g:changed').on('g:changed', function () {
                    this.folderCount = this.folderListView.collection.length;
                    this._childCountCheck();
                }, this);

        if (this.parentModel.resourceName === 'folder') {
            this._initFolderViewSubwidgets();
        } else {
            this.itemCount = 0;
        }

        if (this.parentModel.resourceName === 'folder') {
            this._fetchToRoot(this.parentModel);
        } else {
            this.render();
        }
        events.on('g:login', this.constructor.resetPickedResources, this);
    },

    /**
     * If both the child folders and child items have been fetched, and
     * there are neither of either type in this parent container, we should
     * show the "empty container" message.
     */
    _childCountCheck: function () {
        var container = this.$('.g-empty-parent-message').addClass('hide');
        if (this.folderCount === 0 && this.itemCount === 0) {
            container.removeClass('hide');
        }
    },

    /**
     * Initializes the subwidgets that are only shown when the parent resource
     * is a folder type.
     */
    _initFolderViewSubwidgets: function () {
        this.itemListView = new ItemListWidget({
            folderId: this.parentModel.get('_id'),
            checkboxes: this._checkboxes,
            parentView: this
        });
        this.itemListView.on('g:itemClicked', this._onItemClick, this)
            .off('g:checkboxesChanged')
            .on('g:checkboxesChanged', this.updateChecked, this)
            .off('g:changed').on('g:changed', function () {
                this.itemCount = this.itemListView.collection.length;
                this._childCountCheck();
            }, this);

        this.metadataWidget = new MetadataWidget({
            item: this.parentModel,
            parentView: this,
            accessLevel: this.parentModel.getAccessLevel()
        });
    },

    _setRoute: function () {
        if (this._routing) {
            var route = this.breadcrumbs[0].resourceName + '/' +
                this.breadcrumbs[0].get('_id');
            if (this.parentModel.resourceName === 'folder') {
                route += '/folder/' + this.parentModel.get('_id');
            }
            router.navigate(route);
            events.trigger('g:hierarchy.route', {route: route});
        }
    },

    _fetchToRoot: function (folder) {
        var parentId = folder.get('parentId');
        var parentType = folder.get('parentCollection');
        var modelName = getModelClassByName(parentType);
        if (allModels[modelName]) {
            var parent = new allModels[modelName]();
            parent.set({
                _id: parentId
            }).once('g:fetched', function () {
                this.breadcrumbs.push(parent);
                if (parentType === 'folder') {
                    this._fetchToRoot(parent);
                } else {
                    this.breadcrumbs.reverse();
                    this.render();
                }
            }, this).fetch();
        } else {
            throw new Error('No such model: ' + modelName);
        }
    },

    render: function () {
        this.folderCount = null;
        this.itemCount = null;

        this.$el.html(HierarchyWidgetTemplate({
            type: this.parentModel.resourceName,
            model: this.parentModel,
            level: this.parentModel.getAccessLevel(),
            AccessType: AccessType,
            showActions: this._showActions,
            checkboxes: this._checkboxes,
            capitalize: capitalize
        }));

        if (this.$('.g-folder-actions-menu>li>a').length === 0) {
            // Disable the actions button if actions list is empty
            this.$('.g-folder-actions-button').attr('disabled', 'disabled');
        }

        this.breadcrumbView.setElement(this.$('.g-hierarchy-breadcrumb-bar>ol')).render();
        this.checkedMenuWidget.dropdownToggle = this.$('.g-checked-actions-button');
        this.checkedMenuWidget.setElement(this.$('.g-checked-actions-menu')).render();
        this.folderListView.setElement(this.$('.g-folder-list-container')).render();

        if (this.parentModel.resourceName === 'folder' && this._showItems) {
            this.itemListView.setElement(this.$('.g-item-list-container')).render();
            this.metadataWidget.setItem(this.parentModel);
            this.metadataWidget.setElement(this.$('.g-folder-metadata')).render();
        }

        this.$('[title]').tooltip({
            container: this.$el,
            animation: false,
            delay: {
                show: 100
            },
            placement: function () {
                return this.$element.attr('placement') || 'top';
            }
        });

        if (this.upload) {
            this.uploadDialog();
        } else if (this.folderAccess) {
            this.editAccess();
        } else if (this.folderCreate) {
            this.createFolderDialog();
        } else if (this.folderEdit) {
            this.editFolderDialog();
        } else if (this.itemCreate) {
            this.createItemDialog();
        }

        this.fetchAndShowChildCount();

        return this;
    },

    /**
     * Descend into the given folder.
     */
    descend: function (folder) {
        this.breadcrumbs.push(folder);
        this.setCurrentModel(folder);
    },

    /**
     * Go to the parent of the current folder
     */
    upOneLevel: function () {
        this.breadcrumbs.pop();
        this.setCurrentModel(this.breadcrumbs[this.breadcrumbs.length - 1]);
    },

    /**
     * Prompt the user to create a new subfolder in the current folder.
     */
    createFolderDialog: function () {
        new EditFolderWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel,
            parentView: this
        }).on('g:saved', function (folder) {
            this.folderListView.insertFolder(folder);
            if (this.parentModel.has('nFolders')) {
                this.parentModel.increment('nFolders');
            }
            this.updateChecked();
        }, this).render();
    },

    /**
     * Prompt the user to create a new item in the current folder
     */
    createItemDialog: function () {
        new EditItemWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel,
            parentView: this
        }).on('g:saved', function (item) {
            this.itemListView.insertItem(item);
            if (this.parentModel.has('nItems')) {
                this.parentModel.increment('nItems');
            }
            this.updateChecked();
        }, this).render();
    },

    /**
     * Prompt user to edit the current folder or collection.
     */
    editFolderDialog: function () {
        if (this.parentModel.resourceName === 'folder') {
            new EditFolderWidget({
                el: $('#g-dialog-container'),
                parentModel: this.parentModel,
                folder: this.parentModel,
                parentView: this
            }).on('g:saved', function () {
                events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Folder info updated.',
                    type: 'success',
                    timeout: 4000
                });
                this.breadcrumbView.render();
            }, this).on('g:fileUploaded', function (args) {
                var item = new ItemModel({
                    _id: args.model.get('itemId')
                });

                item.once('g:fetched', function () {
                    this.itemListView.insertItem(item);
                    if (this.parentModel.has('nItems')) {
                        this.parentModel.increment('nItems');
                    }
                    this.updateChecked();
                }, this).fetch();
            }, this).render();
        } else if (this.parentModel.resourceName === 'collection') {
            new EditCollectionWidget({
                el: $('#g-dialog-container'),
                model: this.parentModel,
                parentView: this
            }).on('g:saved', function () {
                this.breadcrumbView.render();
                this.trigger('g:collectionChanged');
            }, this).render();
        }
    },

    /**
     * Prompt the user to delete the currently viewed folder or collection.
     */
    deleteFolderDialog: function () {
        var type = this.parentModel.resourceName;
        var params = {
            text: 'Are you sure you want to delete the ' + type + ' <b>' +
                  this.parentModel.escape('name') + '</b>?',
            escapedHtml: true,
            yesText: 'Delete',
            confirmCallback: _.bind(function () {
                this.parentModel.on('g:deleted', function () {
                    if (type === 'collection') {
                        router.navigate('collections', {trigger: true});
                    } else if (type === 'folder') {
                        this.breadcrumbs.pop();
                        this.setCurrentModel(this.breadcrumbs.slice(-1)[0]);
                    }
                }, this).destroy({
                    throwError: true,
                    progress: true
                });
            }, this)
        };
        confirm(params);
    },

    /**
     * Deprecated alias for showInfoDialog.
     * @deprecated
     */
    folderInfoDialog: function () {
        this.showInfoDialog();
    },

    showInfoDialog: function () {
        var opts = {
            el: $('#g-dialog-container'),
            model: this.parentModel,
            parentView: this
        };

        if (this.parentModel.resourceName === 'collection') {
            new CollectionInfoWidget(opts).render();
        } else if (this.parentModel.resourceName === 'folder') {
            new FolderInfoWidget(opts).render();
        }
    },

    fetchAndShowChildCount: function () {
        this.$('.g-child-count-container').addClass('hide');

        var showCounts = _.bind(function () {
            this.$('.g-child-count-container').removeClass('hide');
            this.$('.g-subfolder-count').text(
                formatCount(this.parentModel.get('nFolders')));
            if (this.parentModel.has('nItems')) {
                this.$('.g-item-count').text(
                    formatCount(this.parentModel.get('nItems')));
            }
        }, this);

        if (this.parentModel.has('nFolders')) {
            showCounts();
        } else {
            this.parentModel.set('nFolders', 0); // prevents fetching details twice
            this.parentModel.once('g:fetched.details', function () {
                showCounts();
            }, this).fetch({extraPath: 'details'});
        }

        this.parentModel.off('change:nItems', showCounts, this)
                        .on('change:nItems', showCounts, this)
                        .off('change:nFolders', showCounts, this)
                        .on('change:nFolders', showCounts, this);

        return this;
    },

    /**
     * Change the current parent model, i.e. the resource being shown currently.
     *
     * @param parent The parent model to change to.
     */
    setCurrentModel: function (parent, opts) {
        opts = opts || {};
        this.parentModel = parent;

        this.breadcrumbView.objects = this.breadcrumbs;

        this.folderListView.initialize({
            parentType: parent.resourceName,
            parentId: parent.get('_id'),
            checkboxes: this._checkboxes
        });

        this.updateChecked();

        if (parent.resourceName === 'folder') {
            if (this.itemListView) {
                this.itemListView.initialize({
                    folderId: parent.get('_id'),
                    checkboxes: this._checkboxes
                });
            } else {
                this._initFolderViewSubwidgets();
            }
        }

        this.render();
        if (!_.has(opts, 'setRoute') || opts.setRoute) {
            this._setRoute();
        }
        this.trigger('g:setCurrentModel');
    },

    /**
     * Based on a resource collection with either has model references or
     * checkbox references, return a string that describes the collection.
     * :param resources: a hash with different resources.
     * :returns: description of the resources.
     */
    _describeResources: function (resources) {
        /* If the resources aren't English words or don't have simple plurals,
         * this will need to be refactored. */
        var kinds = ['folder', 'item'];

        var desc = [];
        for (var i = 0; i < kinds.length; i += 1) {
            var kind = kinds[i];
            if (resources[kind] && resources[kind].length) {
                desc.push(resources[kind].length + ' ' + kind +
                          (resources[kind].length !== 1 ? 's' : ''));
            }
        }
        switch (desc.length) {
            case 0:
                return 'nothing';
            case 1:
                return desc[0];
            case 2:
                return desc[0] + ' and ' + desc[1];
            /* If we add a third model type, enable this:
            default:
                desc[desc.length-1] = 'and ' + desc[desc.length-1];
                return ', '.join(desc);
             */
        }
    },

    /**
     * Prompt the user to delete the currently checked items.
     */
    deleteCheckedDialog: function () {
        var view = this;
        var folders = this.folderListView.checked;
        var items;
        if (this.itemListView && this.itemListView.checked.length) {
            items = this.itemListView.checked;
        }
        var desc = this._describeResources({folder: folders, item: items});

        var params = {
            text: 'Are you sure you want to delete the checked resources (' +
                  desc + ')?',

            yesText: 'Delete',
            confirmCallback: function () {
                var resources = view._getCheckedResourceParam();
                /* Content on DELETE requests is somewhat oddly supported (I
                 * can't get it to work under jasmine/phantom), so override the
                 * method. */
                restRequest({
                    path: 'resource',
                    type: 'POST',
                    data: {resources: resources, progress: true},
                    headers: {'X-HTTP-Method-Override': 'DELETE'}
                }).done(function () {
                    if (items && items.length && view.parentModel.has('nItems')) {
                        view.parentModel.increment('nItems', -items.length);
                    }
                    if (folders.length && view.parentModel.has('nFolders')) {
                        view.parentModel.increment('nFolders', -folders.length);
                    }

                    view.setCurrentModel(view.parentModel, {setRoute: false});
                });
            }
        };
        confirm(params);
    },

    /**
     * Show and handle the upload dialog
     */
    uploadDialog: function () {
        var container = $('#g-dialog-container');

        new UploadWidget({
            el: container,
            parent: this.parentModel,
            parentType: this.parentType,
            parentView: this
        }).on('g:uploadFinished', function (info) {
            handleClose('upload');
            this.upload = false;
            if (this.parentModel.has('nItems')) {
                this.parentModel.increment('nItems', info.files.length);
            }
            if (this.parentModel.has('size')) {
                this.parentModel.increment('size', info.totalSize);
            }
            this.setCurrentModel(this.parentModel, {setRoute: false});
        }, this).render();
    },

    /**
     * When any of the checkboxes is changed, this will be called to update
     * the checked menu state.
     */
    updateChecked: function () {
        var folders = this.folderListView.checked,
            items = [];

        // Only show actions corresponding to the minimum access level over
        // the whole set of checked resources.
        var minFolderLevel = AccessType.ADMIN;
        _.every(folders, function (cid) {
            var folder = this.folderListView.collection.get(cid);
            minFolderLevel = Math.min(minFolderLevel, folder.getAccessLevel());
            return minFolderLevel > AccessType.READ; // acts as 'break'
        }, this);

        var minItemLevel = AccessType.ADMIN;
        if (this.itemListView) {
            items = this.itemListView.checked;
            if (items.length) {
                minItemLevel = Math.min(minItemLevel, this.parentModel.getAccessLevel());
            }
        }

        if (folders.length + items.length) {
            // Disable folder actions if checkboxes are checked
            this.$('.g-folder-actions-button').attr('disabled', 'disabled');
        } else {
            this.$('.g-folder-actions-button').removeAttr('disabled');
        }

        this.checkedMenuWidget.update({
            minFolderLevel: minFolderLevel,
            minItemLevel: minItemLevel,
            folderCount: folders.length,
            itemCount: items.length,
            pickedCount: this.getPickedCount(),
            pickedCopyAllowed: this.getPickedCopyAllowed(),
            pickedMoveAllowed: this.getPickedMoveAllowed(),
            pickedDesc: this.getPickedDescription()
        });
    },

    getPickedCount: function () {
        var pickedCount = 0;
        if (pickedResources && pickedResources.resources) {
            _.each(pickedResources.resources, function (list) {
                pickedCount += list.length;
            });
        }
        return pickedCount;
    },

    getPickedCopyAllowed: function () {
        /* We must have something picked */
        if (!pickedResources) {
            return false;
        }
        /* If we have an item picked but this page isn't a folder's list, then
         * you can't move or copy them here. */
        if (this.parentModel.resourceName !== 'folder') {
            if (pickedResources.resources.item &&
                    pickedResources.resources.item.length) {
                return false;
            }
        }
        /* We must have permission to write to this folder to be allowed to
         * copy. */
        if (this.parentModel.getAccessLevel() < AccessType.WRITE) {
            return false;
        }
        return true;
    },

    getPickedMoveAllowed: function () {
        /* All of the restrictions for copy are the same */
        if (!this.getPickedCopyAllowed()) {
            return false;
        }
        /* We also can't move an item or folder if we don't have permission to
         * delete that item or folder (since a move deletes it from the
         * original spot). */
        if (pickedResources.minFolderLevel < AccessType.ADMIN) {
            return false;
        }
        if (pickedResources.minItemLevel < AccessType.WRITE) {
            return false;
        }
        return true;
    },

    getPickedDescription: function () {
        if (!pickedResources || !pickedResources.resources) {
            return '';
        }
        return this._describeResources(pickedResources.resources);
    },

    /**
     * Get a parameter that can be added to a url for the checked resources.
     */
    _getCheckedResourceParam: function (asObject) {
        var resources = {folder: [], item: []};
        var folders = this.folderListView.checked;
        _.each(folders, function (cid) {
            var folder = this.folderListView.collection.get(cid);
            resources.folder.push(folder.id);
        }, this);
        if (this.itemListView) {
            var items = this.itemListView.checked;
            _.each(items, function (cid) {
                var item = this.itemListView.collection.get(cid);
                resources.item.push(item.id);
                return true;
            }, this);
        }
        _.each(resources, function (list, key) {
            if (!list.length) {
                delete resources[key];
            }
        });
        if (asObject) {
            return resources;
        }
        return JSON.stringify(resources);
    },

    downloadChecked: function () {
        var url = apiRoot + '/resource/download';
        var resources = this._getCheckedResourceParam();
        var data = {resources: resources};

        this.redirectViaForm('POST', url, data);
    },

    pickChecked: function () {
        if (!pickedResources) {
            pickedResources = {
                resources: {},
                minItemLevel: AccessType.ADMIN,
                minFolderLevel: AccessType.ADMIN
            };
        }
        /* Maintain our minimum permissions.  It is expensive to compute them
         * arbitrarily later. */
        var folders = this.folderListView.checked;
        _.every(folders, function (cid) {
            var folder = this.folderListView.collection.get(cid);
            pickedResources.minFolderLevel = Math.min(
                pickedResources.minFolderLevel,
                folder.getAccessLevel());
            return (pickedResources.minFolderLevel >
                    AccessType.READ); // acts as 'break'
        }, this);
        if (this.itemListView) {
            var items = this.itemListView.checked;
            if (items.length) {
                pickedResources.minItemLevel = Math.min(
                    pickedResources.minItemLevel,
                    this.parentModel.getAccessLevel());
            }
        }
        var resources = this._getCheckedResourceParam(true);
        var pickDesc = this._describeResources(resources);
        /* Merge these resources with any that are already picked */
        var existing = pickedResources.resources;
        _.each(existing, function (list, resource) {
            if (!resources[resource]) {
                resources[resource] = list;
            } else {
                resources[resource] = _.union(list, resources[resource]);
            }
        });
        pickedResources.resources = resources;
        this.updateChecked();
        var totalPickDesc = this.getPickedDescription();
        var desc = totalPickDesc + ' picked.';
        if (pickDesc !== totalPickDesc) {
            desc = pickDesc + ' added to picked resources.  Now ' + desc;
        }
        events.trigger('g:alert', {
            icon: 'ok',
            text: desc,
            type: 'info',
            timeout: 4000
        });
    },

    _incrementCounts: function (nFolders, nItems) {
        if (this.parentModel.has('nItems')) {
            this.parentModel.increment('nItems', nItems);
        }
        if (this.parentModel.has('nFolders')) {
            this.parentModel.increment('nFolders', nFolders);
        }
    },

    movePickedResources: function () {
        if (!this.getPickedMoveAllowed()) {
            return;
        }
        var resources = JSON.stringify(pickedResources.resources);
        var nFolders = (pickedResources.resources.folder || []).length;
        var nItems = (pickedResources.resources.item || []).length;
        restRequest({
            path: 'resource/move',
            type: 'PUT',
            data: {
                resources: resources,
                parentType: this.parentModel.resourceName,
                parentId: this.parentModel.get('_id'),
                progress: true
            }
        }).done(_.bind(function () {
            this._incrementCounts(nFolders, nItems);
            this.setCurrentModel(this.parentModel, {setRoute: false});
        }, this));
        this.clearPickedResources();
    },

    copyPickedResources: function () {
        if (!this.getPickedCopyAllowed()) {
            return;
        }
        var resources = JSON.stringify(pickedResources.resources);
        var nFolders = (pickedResources.resources.folder || []).length;
        var nItems = (pickedResources.resources.item || []).length;
        restRequest({
            path: 'resource/copy',
            type: 'POST',
            data: {
                resources: resources,
                parentType: this.parentModel.resourceName,
                parentId: this.parentModel.get('_id'),
                progress: true
            }
        }).done(_.bind(function () {
            this._incrementCounts(nFolders, nItems);
            this.setCurrentModel(this.parentModel, {setRoute: false});
        }, this));
        this.clearPickedResources();
    },

    clearPickedResources: function (event) {
        this.constructor.resetPickedResources();
        this.updateChecked();
        if (event) {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Cleared picked resources',
                type: 'info',
                timeout: 4000
            });
        }
    },

    redirectViaForm: function (method, url, data) {
        var form = $('<form action="' + url + '" method="' + method + '"/>');
        _.each(data, function (value, key) {
            form.append($('<input/>').attr({type: 'text', name: key, value: value}));
        });
        // $(form).submit() will *not* work w/ Firefox (http://stackoverflow.com/q/7117084/250457)
        $(form).appendTo('body').submit();
    },

    editAccess: function () {
        new AccessWidget({
            el: $('#g-dialog-container'),
            modelType: this.parentModel.resourceName,
            model: this.parentModel,
            parentView: this
        }).on('g:accessListSaved', function (params) {
            if (params.recurse) {
                // Refresh list since the public flag may have changed on the children.
                this.refreshFolderList();
            }
        }, this);
    },

    /**
     * Deprecated alias for editAccess.
     * @deprecated
     */
    editFolderAccess: function () {
        this.editAccess();
    },

    /**
     * Reloads the folder list view.
     */
    refreshFolderList: function () {
        this.folderListView.collection.fetch(null, true);
    },

    /**
     * Select (highlight) an item in the list.
     * @param item An ItemModel instance representing the item to select.
     */
    selectItem: function (item) {
        this.itemListView.selectItem(item);
    },

    /**
     * Return the currently selected item, or null if there is no selected item.
     */
    getSelectedItem: function () {
        return this.itemListView.getSelectedItem();
    },

    /**
     * In order to handle range selection, we must listen to checkbox changes
     * at this level, in case a range selection crosses the boundary between
     * folders and items.
     */
    checkboxListener: function (e) {
        var checkbox = $(e.currentTarget);

        if (this._lastCheckbox) {
            if (e.shiftKey) {
                var checkboxes = this.$el.find(':checkbox');
                var from = checkboxes.index(this._lastCheckbox);
                var to = checkboxes.index(checkbox);

                checkboxes.slice(Math.min(from, to), Math.max(from, to) + 1)
                    .prop('checked', checkbox.prop('checked'));

                this.folderListView.recomputeChecked();

                if (this.itemListView) {
                    this.itemListView.recomputeChecked();
                }

                this.updateChecked();
            }
        }
        this._lastCheckbox = checkbox;
    }
}, {
    /* Because we need to be able to clear picked resources when the current user
     * changes, this function is placed in the girder namespace. */
    resetPickedResources: function (val) {
        pickedResources = val || null;
    },
    getPickedResources: function () {
        return pickedResources;
    }
});

export default HierarchyWidget;
