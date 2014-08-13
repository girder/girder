/**
 * This widget is used to navigate the data hierarchy of folders and items.
 */
girder.views.HierarchyWidget = girder.View.extend({
    events: {
        'click a.g-create-subfolder': 'createFolderDialog',
        'click a.g-edit-folder': 'editFolderDialog',
        'click a.g-download-folder': 'downloadFolder',
        'click a.g-delete-folder': 'deleteFolderDialog',
        'click a.g-create-item': 'createItemDialog',
        'click .g-upload-here-button': 'uploadDialog',
        'click .g-folder-access-button': 'editFolderAccess',
        'click .g-hierarchy-level-up': 'upOneLevel'
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
     * This should be instantiated with the following properties:
     * -parentModel: The model representing the root node. Must be a User,
                     Collection, or Folder model.
     */
    initialize: function (settings) {
        this.parentModel = settings.parentModel;
        this.upload = settings.upload;
        this.access = settings.access;
        this.edit = settings.edit;

        this.breadcrumbs = [this.parentModel];

        if (this.parentModel.resourceName === 'folder') {
            this._fetchToRoot(this.parentModel);
        }
        else {
            this.render();
        }
    },

    _setRoute: function () {
        var route = this.breadcrumbs[0].resourceName + '/' +
            this.breadcrumbs[0].get('_id');
        if (this.parentModel.resourceName === 'folder') {
            route += '/folder/' + this.parentModel.get('_id');
        }
        girder.router.navigate(route);
    },

    _fetchToRoot: function (folder) {
        var parentId = folder.get('parentId');
        var parentType = folder.get('parentCollection');
        var parent = new girder.models[girder.getModelClassByName(parentType)]();
        parent.set({
            _id: parentId
        }).on('g:fetched', function () {
            this.breadcrumbs.push(parent);

            if (parentType === 'folder') {
                this._fetchToRoot(parent);
            }
            else {
                this.breadcrumbs.reverse();
                this.render();
            }
        }, this).fetch();
    },

    render: function () {
        this.folderCount = null;
        this.itemCount = null;

        this.$el.html(jade.templates.hierarchyWidget({
            type: this.parentModel.resourceName,
            model: this.parentModel,
            level: this.parentModel.getAccessLevel(),
            AccessType: girder.AccessType
        }));

        var view = this;
        this.$('.g-select-all').unbind('change').change(function () {
            view.folderListView.checkAll(this.checked);

            if (view.itemListView) {
                view.itemListView.checkAll(this.checked);
            }
        });

        if (this.$('.g-folder-actions-menu>li>a').length === 0) {
            // Disable the actions button if actions list is empty
            this.$('.g-folder-actions-button').attr('disabled', 'disabled');
        }

        // Initialize the breadcrumb bar state
        this.breadcrumbView = new girder.views.HierarchyBreadcrumbView({
            el: this.$('.g-hierarchy-breadcrumb-bar>ol'),
            objects: this.breadcrumbs
        });
        this.breadcrumbView.on('g:breadcrumbClicked', function (idx) {
            this.parentModel = this.breadcrumbs[idx];
            this.breadcrumbs = this.breadcrumbs.slice(0, idx + 1);
            this.render();
            this._setRoute();
        }, this);

        this.checkedMenuWidget = new girder.views.CheckedMenuWidget({
            el: this.$('.g-checked-actions-menu'),
            dropdownToggle: this.$('.g-checked-actions-button')
        });

        // Setup the child folder list view
        this.folderListView = new girder.views.FolderListWidget({
            parentType: this.parentModel.resourceName,
            parentId: this.parentModel.get('_id'),
            el: this.$('.g-folder-list-container')
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
            // Setup the child item list view
            this.itemListView = new girder.views.ItemListWidget({
                folderId: this.parentModel.get('_id'),
                el: this.$('.g-item-list-container')
            });
            this.itemListView.on('g:itemClicked', function (item) {
                girder.router.navigate('item/' + item.get('_id'), {trigger: true});
            }, this).off('g:checkboxesChanged')
                    .on('g:checkboxesChanged', this.updateChecked, this)
                    .off('g:changed').on('g:changed', function () {
                this.itemCount = this.itemListView.collection.length;
                this._childCountCheck();
            }, this);
        }
        else {
            this.itemCount = 0;
        }

        this.$('.g-folder-info-button,.g-folder-access-button,.g-select-all,' +
               '.g-upload-here-button,.g-checked-actions-button').tooltip({
            container: this.$el,
            animation: false,
            delay: {show: 100}
        });
        this.$('.g-folder-actions-button,.g-hierarchy-level-up').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        if (this.upload) {
            this.uploadDialog();
        } else if (this.access) {
            this.editFolderAccess();
        } else if (this.edit) {
            this.editFolderDialog();
        }

        return this;
    },

    /**
     * Descend into the given folder.
     */
    descend: function (folder) {
        this.breadcrumbs.push(folder);
        this.parentModel = folder;
        this.render();
        this._setRoute();
    },

    /**
     * Go to the parent of the current folder
     */
    upOneLevel: function () {
        this.breadcrumbs.pop();
        this.parentModel = this.breadcrumbs[this.breadcrumbs.length - 1];
        this.render();
        this._setRoute();
    },

    /**
     * Prompt the user to create a new subfolder in the current folder.
     */
    createFolderDialog: function () {
        new girder.views.EditFolderWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel
        }).on('g:saved', function (folder) {
            this.folderListView.insertFolder(folder);
            this.updateChecked();
        }, this).render();
    },

    /**
     * Prompt the user to create a new item in the current folder
     */
    createItemDialog: function () {
        new girder.views.EditItemWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel
        }).on('g:saved', function (item) {
            this.itemListView.insertItem(item);
            this.updateChecked();
        }, this).render();
    },

    /**
     * Prompt user to edit the current folder
     */
    editFolderDialog: function () {
        new girder.views.EditFolderWidget({
            el: $('#g-dialog-container'),
            parentModel: this.parentModel,
            folder: this.parentModel
        }).on('g:saved', function (folder) {
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'Folder info updated.',
                type: 'success',
                timeout: 4000
            });
            this.breadcrumbView.render();
        }, this).render();
    },

    /**
     * Prompt the user to delete the currently viewed folder.
     */
    deleteFolderDialog: function () {
        var view = this;
        var params = {
            text: 'Are you sure you want to delete the folder <b>' +
                  this.parentModel.get('name') + '</b>?',
            yesText: 'Delete',
            confirmCallback: function () {
                view.parentModel.destroy().on('g:deleted', function () {
                    this.breadcrumbs.pop();
                    this.parentModel = this.breadcrumbs.slice(-1)[0];
                    this.render();
                }, view);
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
            folder: this.parentModel
        }).on('g:uploadFinished', function () {
            girder.dialogs.handleClose('upload');
            this.upload = false;
            this.render();
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

        this.checkedMenuWidget.update({
            minFolderLevel: minFolderLevel,
            minItemLevel: minItemLevel,
            folderCount: folders.length,
            itemCount: items.length
        });
    },

    downloadFolder: function () {
        window.location = girder.apiRoot + '/folder/' +
           this.parentModel.get('_id') + '/download';
    },

    editFolderAccess: function () {
        new girder.views.AccessWidget({
            el: $('#g-dialog-container'),
            modelType: this.parentModel.resourceName,
            model: this.parentModel
        }).on('g:saved', function (folder) {
            // need to do anything?
        }, this);
    }
});

/**
 * Renders the breadcrumb list in the hierarchy widget.
 */
girder.views.HierarchyBreadcrumbView = girder.View.extend({
    events: {
        'click a.g-breadcrumb-link': function (event) {
            var link = $(event.currentTarget);
            this.trigger('g:breadcrumbClicked', parseInt(link.attr('g-index'), 10));
        }
    },

    initialize: function (settings) {
        this.objects = settings.objects;
        this.render();
    },

    render: function () {
        // Clone the array so we don't alter the instance's copy
        var objects = this.objects.slice(0);

        // Pop off the last object, it refers to the currently viewed
        // object and should be the "active" class, and not a link.
        var active = objects.pop();

        this.$el.html(jade.templates.hierarchyBreadcrumb({
            links: objects,
            current: active
        }));
    }
});
