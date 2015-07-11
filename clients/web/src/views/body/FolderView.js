/**
 * This view shows a single folder as a hierarchy widget.
 */
girder.views.FolderView = girder.View.extend({
    initialize: function (settings) {
        girder.cancelRestRequests('fetch');
        this.folder = settings.folder;
        this.upload = settings.upload || false;
        this.folderAccess = settings.folderAccess || false;
        this.folderCreate = settings.folderCreate || false;
        this.folderEdit = settings.folderEdit || false;
        this.itemCreate = settings.itemCreate || false;

        this.hierarchyWidget = new girder.views.HierarchyWidget({
            parentModel: this.folder,
            upload: this.upload,
            folderAccess: this.folderAccess,
            folderEdit: this.folderEdit,
            folderCreate: this.folderCreate,
            itemCreate: this.itemCreate,
            parentView: this
        });

        this.render();
    },

    render: function () {
        this.hierarchyWidget.setElement(this.$el).render();
        return this;
    }
});

girder.router.route('folder/:id', 'folder', function (id, params) {
    // Fetch the folder by id, then render the view.
    var folder = new girder.models.FolderModel();
    folder.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.FolderView, _.extend({
            folder: folder,
            upload: params.dialog === 'upload',
            folderAccess: params.dialog === 'folderaccess',
            folderCreate: params.dialog === 'foldercreate',
            folderEdit: params.dialog === 'folderedit',
            itemCreate: params.dialog === 'itemcreate'
        }, params || {}));
    }, this).fetch();
});
