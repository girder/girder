/**
 * This widget is used to navigate the data hierarchy of folders and items.
 */
girder.views.HierarchyWidget = girder.View.extend({
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
        this.navigate = settings.navigate || false;

        this._showActions = _.has(settings, 'showActions') ? settings.showActions : true;
        this._showItems = _.has(settings, 'showItems') ? settings.showItems : true;
        this._checkboxes = _.has(settings, 'checkboxes') ? settings.checkboxes : true;
        this._routing = _.has(settings, 'routing') ? settings.routing : true;
        this._appendPages = _.has(settings, 'appendPages') ? settings.appendPages : false;
        this._onItemClick = settings.onItemClick || (
            this.navigate ? this.$.noop : function (item) {
                girder.router.navigate('item/' + item.id, {trigger: true});
            });

        this.folderAccess = settings.folderAccess;
        this.folderCreate = settings.folderCreate;
        this.folderEdit = settings.folderEdit;
        this.itemCreate = settings.itemCreate;
        this.breadcrumbs = [this.parentModel];

        // Initialize the breadcrumb bar state
        this.breadcrumbView = new girder.views.HierarchyBreadcrumbView({
            objects: this.breadcrumbs,
            parentView: this
        });
        this.breadcrumbView.on('g:breadcrumbClicked', function (idx) {
            this.breadcrumbs = this.breadcrumbs.slice(0, idx + 1);
            this.setCurrentModel(this.breadcrumbs[idx]);
            this._setRoute();
        }, this);

        this.checkedMenuWidget = new girder.views.CheckedMenuWidget({
            pickedCount: this.getPickedCount(),
            pickedCopyAllowed: this.getPickedCopyAllowed(),
            pickedMoveAllowed: this.getPickedMoveAllowed(),
            pickedDesc: this.getPickedDescription(),
            parentView: this
        });

        this.folderListView = new girder.views.FolderListWidget({
            parentType: this.parentModel.resourceName,
            parentId: this.parentModel.get('_id'),
            checkboxes: this._checkboxes,
            navigate: this.navigate,
            parentView: this
        });
        this.folderListView.on('g:folderClicked', function (folder) {
            if (!this.navigate) {
                this.descend(folder);

                if (this.uploadWidget) {
                    this.uploadWidget.folder = folder;
                }
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
        girder.events.on('g:login', girder.resetPickedResources, this);
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
        this.itemListView = new girder.views.ItemListWidget({
            folderId: this.parentModel.get('_id'),
            checkboxes: this._checkboxes,
            navigate: this.navigate,
            parentView: this
        });
        this.itemListView.on('g:itemClicked', this._onItemClick, this)
            .off('g:checkboxesChanged')
            .on('g:checkboxesChanged', this.updateChecked, this)
            .off('g:changed').on('g:changed', function () {
                this.itemCount = this.itemListView.collection.length;
                this._childCountCheck();
            }, this);

        this.metadataWidget = new girder.views.MetadataWidget({
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
            girder.router.navigate(route);
            girder.events.trigger('g:hierarchy.route', {route: route});
        }
    },

    _fetchToRoot: function (folder) {
        var parentId = folder.get('parentId');
        var parentType = folder.get('parentCollection');
        var parent = new girder.models[girder.getModelClassByName(parentType)]();
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
    },

    render: function () {
        this.folderCount = null;
        this.itemCount = null;

        this.$el.html(girder.templates.hierarchyWidget({
            type: this.parentModel.resourceName,
            model: this.parentModel,
            level: this.parentModel.getAccessLevel(),
            AccessType: girder.AccessType,
            showActions: this._showActions,
            checkboxes: this._checkboxes,
            girder: girder
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

        if (this.folderListView && this.folderListView.collection && this.itemListView && this.itemListView.collection) {
            this.folderCount = this.folderListView.collection.length;
            this.itemCount = this.itemListView.collection.length;
            this._childCountCheck();
        }

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
     * Prompt the user to create a new subfolder in the current folder.
     */
    createFolderDialog: function () {
        new girder.views.EditFolderWidget({
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
        new girder.views.EditItemWidget({
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
            new girder.views.EditFolderWidget({
                el: $('#g-dialog-container'),
                parentModel: this.parentModel,
                folder: this.parentModel,
                parentView: this
            }).on('g:saved', function () {
                girder.events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Folder info updated.',
                    type: 'success',
                    timeout: 4000
                });
                this.breadcrumbView.render();
            }, this).on('g:fileUploaded', function (args) {
                var item = new girder.models.ItemModel({
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
            new girder.views.EditCollectionWidget({
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
                this.parentModel.destroy({
                    throwError: true,
                    progress: true
                }).on('g:deleted', function () {
                    if (type === 'collection') {
                        girder.router.navigate('collections', {trigger: true});
                    } else if (type === 'folder') {
                        this.breadcrumbs.pop();
                        this.setCurrentModel(this.breadcrumbs.slice(-1)[0]);
                    }
                }, this);
            }, this)
        };
        girder.confirm(params);
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
            new girder.views.CollectionInfoWidget(opts).render();
        } else if (this.parentModel.resourceName === 'folder') {
            new girder.views.FolderInfoWidget(opts).render();
        }
    },

    fetchAndShowChildCount: function () {
        this.$('.g-child-count-container').addClass('hide');

        var showCounts = _.bind(function () {
            this.$('.g-child-count-container').removeClass('hide');
            this.$('.g-subfolder-count').text(
                girder.formatCount(this.parentModel.get('nFolders')));
            if (this.parentModel.has('nItems')) {
                this.$('.g-item-count').text(
                    girder.formatCount(this.parentModel.get('nItems')));
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
                return desc[0] + ' and ' + desc [1];
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
                girder.restRequest({
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
        girder.confirm(params);
    },

    /**
     * Show and handle the upload dialog
     */
    uploadDialog: function () {
        var container = $('#g-dialog-container');

        new girder.views.UploadWidget({
            el: container,
            parent: this.parentModel,
            parentType: this.parentType,
            parentView: this
        }).on('g:uploadFinished', function (info) {
            girder.dialogs.handleClose('upload');
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
        var minFolderLevel = girder.AccessType.ADMIN;
        _.every(folders, function (cid) {
            var folder = this.folderListView.collection.get(cid);
            minFolderLevel = Math.min(minFolderLevel, folder.getAccessLevel());
            return minFolderLevel > girder.AccessType.READ; // acts as 'break'
        }, this);

        var minItemLevel = girder.AccessType.ADMIN;
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
        if (girder.pickedResources && girder.pickedResources.resources) {
            _.each(girder.pickedResources.resources, function (list) {
                pickedCount += list.length;
            });
        }
        return pickedCount;
    },

    getPickedCopyAllowed: function () {
        /* We must have something picked */
        if (!girder.pickedResources) {
            return false;
        }
        /* If we have an item picked but this page isn't a folder's list, then
         * you can't move or copy them here. */
        if (this.parentModel.resourceName !== 'folder') {
            if (girder.pickedResources.resources.item &&
                    girder.pickedResources.resources.item.length) {
                return false;
            }
        }
        /* We must have permission to write to this folder to be allowed to
         * copy. */
        if (this.parentModel.getAccessLevel() < girder.AccessType.WRITE) {
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
        if (girder.pickedResources.minFolderLevel < girder.AccessType.ADMIN) {
            return false;
        }
        if (girder.pickedResources.minItemLevel < girder.AccessType.WRITE) {
            return false;
        }
        return true;
    },

    getPickedDescription: function () {
        if (!girder.pickedResources || !girder.pickedResources.resources) {
            return '';
        }
        return this._describeResources(girder.pickedResources.resources);
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
        var url = girder.apiRoot + '/resource/download';
        var resources = this._getCheckedResourceParam();
        var data = {resources: resources};

        this.redirectViaForm('POST', url, data);
    },

    pickChecked: function () {
        if (!girder.pickedResources) {
            girder.pickedResources = {
                resources: {},
                minItemLevel: girder.AccessType.ADMIN,
                minFolderLevel: girder.AccessType.ADMIN
            };
        }
        /* Maintain our minimum permissions.  It is expensive to compute them
         * arbitrarily later. */
        var folders = this.folderListView.checked;
        _.every(folders, function (cid) {
            var folder = this.folderListView.collection.get(cid);
            girder.pickedResources.minFolderLevel = Math.min(
                girder.pickedResources.minFolderLevel,
                folder.getAccessLevel());
            return (girder.pickedResources.minFolderLevel >
                    girder.AccessType.READ); // acts as 'break'
        }, this);
        if (this.itemListView) {
            var items = this.itemListView.checked;
            if (items.length) {
                girder.pickedResources.minItemLevel = Math.min(
                    girder.pickedResources.minItemLevel,
                    this.parentModel.getAccessLevel());
            }
        }
        var resources = this._getCheckedResourceParam(true);
        var pickDesc = this._describeResources(resources);
        /* Merge these resources with any that are already picked */
        var existing = girder.pickedResources.resources;
        _.each(existing, function (list, resource) {
            if (!resources[resource]) {
                resources[resource] = list;
            } else {
                resources[resource] = _.union(list, resources[resource]);
            }
        });
        girder.pickedResources.resources = resources;
        this.updateChecked();
        var totalPickDesc = this.getPickedDescription();
        var desc = totalPickDesc + ' picked.';
        if (pickDesc !== totalPickDesc) {
            desc = pickDesc + ' added to picked resources.  Now ' + desc;
        }
        girder.events.trigger('g:alert', {
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
        var resources = JSON.stringify(girder.pickedResources.resources);
        var nFolders = (girder.pickedResources.resources.folder || []).length;
        var nItems = (girder.pickedResources.resources.item || []).length;
        girder.restRequest({
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
        var resources = JSON.stringify(girder.pickedResources.resources);
        var nFolders = (girder.pickedResources.resources.folder || []).length;
        var nItems = (girder.pickedResources.resources.item || []).length;
        girder.restRequest({
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
        girder.resetPickedResources();
        this.updateChecked();
        if (event) {
            girder.events.trigger('g:alert', {
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
            form.append($('<input/>').attr(
                {type: 'text', name: key, value: value}));
        });
        $(form).submit();
    },

    editAccess: function () {
        new girder.views.AccessWidget({
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
});

/* Because we need to be able to clear picked resources when the current user
 * changes, this function is placed in the girder namespace. */
girder.resetPickedResources = function () {
    girder.pickedResources = null;
};

/**
 * Renders the breadcrumb list in the hierarchy widget.
 */
girder.views.HierarchyBreadcrumbView = girder.View.extend({
    initialize: function (settings) {
        this.objects = settings.objects;
    },

    render: function () {
        // Clone the array so we don't alter the instance's copy
        var objects = this.objects.slice(0);

        // Pop off the last object, it refers to the currently viewed
        // object and should be the "active" class, and not a link.
        var active = objects.pop();

        var descriptionText = $(girder.renderMarkdown(
            active.get('description') || '')).text();

        this.$el.html(girder.templates.hierarchyBreadcrumb({
            links: objects,
            current: active,
            descriptionText: descriptionText
        }));
    }
});
