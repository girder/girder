/**
 * This widget is used to navigate the data hierarchy of folders and items.
 */
girder.views.HierarchyWidget = Backbone.View.extend({
    events: {
        'click a.g-create-subfolder': 'createFolderDialog',
        'click a.g-download-folder': 'downloadFolder',
        'click a.g-delete-folder': 'deleteFolderDialog',
        'click .g-upload-here-button': 'uploadDialog',
        'click .g-folder-access-button': 'editFolderAccess'
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

    initialize: function (settings) {
        this.parentType = settings.parentType || 'folder';
        this.parentModel = settings.parentModel;

        this.breadcrumbs = [{
            'type': this.parentType,
            'model': this.parentModel
        }];

        this.render();
    },

    render: function () {
        this.folderCount = null;
        this.itemCount = null;

        this.$el.html(jade.templates.hierarchyWidget({
            type: this.parentType,
            model: this.parentModel,
            level: this.parentModel.get('_accessLevel'),
            AccessType: girder.AccessType
        }));

        var view = this;
        this.$('.g-folder-info-button,.g-folder-access-button,.g-select-all,' +
               '.g-upload-here-button,.g-checked-actions-button').tooltip({
            container: 'body',
            animation: false,
            delay: {show: 100}
        });
        this.$('.g-folder-actions-button').tooltip({
            container: 'body',
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });
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
            this.parentType = this.breadcrumbs[idx].type;
            this.parentModel = this.breadcrumbs[idx].model;
            this.breadcrumbs = this.breadcrumbs.slice(0, idx + 1);

            this.render();
        }, this);

        this.checkedMenuWidget = new girder.views.CheckedMenuWidget({
            el: this.$('.g-checked-actions-menu'),
            dropdownToggle: this.$('.g-checked-actions-button')
        });

        // Setup the child folder list view
        this.folderListView = new girder.views.FolderListWidget({
            parentType: this.parentType,
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

        if (this.parentType === 'folder') {
            // Setup the child item list view
            this.itemListView = new girder.views.ItemListWidget({
                folderId: this.parentModel.get('_id'),
                el: this.$('.g-item-list-container')
            });
            this.itemListView.on('g:itemClicked', function (item) {
                girder.events.trigger('g:navigateTo', girder.views.ItemView, {
                    item: item
                });
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
        return this;
    },

    /**
     * Descend into the given folder.
     */
    descend: function (folder) {
        this.breadcrumbs.push({
            type: 'folder',
            model: folder
        });
        this.parentModel = folder;
        this.parentType = 'folder';
        this.render();
    },

    /**
     * Prompt the user to create a new subfolder in the current folder.
     */
    createFolderDialog: function () {
        new girder.views.EditFolderWidget({
                el: $('#g-dialog-container'),
                parentType: this.parentType,
                parentModel: this.parentModel
        }).on('g:saved', function (folder) {
                this.folderListView.insertFolder(folder);
                this.updateChecked();
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
                    var parent = this.breadcrumbs.slice(-1)[0];
                    this.parentType = parent.type;
                    this.parentModel = parent.model;
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
            // When upload is finished, refresh the folder view
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
        var minLevel = girder.AccessType.ADMIN;
        _.every(folders, function (cid) {
            var folder = this.folderListView.collection.get(cid);
            minLevel = Math.min(minLevel, folder.get('_accessLevel'));
            return minLevel > girder.AccessType.READ; // acts as 'break'
        }, this);

        if (this.itemListView) {
            items = this.itemListView.checked;
            if (items.length) {
                minLevel = Math.min(minLevel, this.parentModel.get('_accessLevel'));
            }
        }

        this.checkedMenuWidget.update({
            minLevel: minLevel,
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
                modelType: this.parentType,
                model: this.parentModel
        }).on('g:saved', function (folder) {
                // need to do anything?
        }, this);
    }
});

/**
 * Renders the breadcrumb list in the hierarchy widget.
 */
girder.views.HierarchyBreadcrumbView = Backbone.View.extend({
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
