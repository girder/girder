var _               = require('underscore');

var girder          = require('girder/init');
var Events          = require('girder/events');
var FolderModel     = require('girder/models/FolderModel');
var HierarchyWidget = require('girder/views/widgets/HierarchyWidget');
var Rest            = require('girder/rest');
var View            = require('girder/view');

/**
 * This view shows a single folder as a hierarchy widget.
 */
var FolderView = View.extend({
    initialize: function (settings) {
        Rest.cancelRestRequests('fetch');
        this.folder = settings.folder;
        this.upload = settings.upload || false;
        this.folderAccess = settings.folderAccess || false;
        this.folderCreate = settings.folderCreate || false;
        this.folderEdit = settings.folderEdit || false;
        this.itemCreate = settings.itemCreate || false;

        this.hierarchyWidget = new HierarchyWidget({
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

module.exports = FolderView;

girder.router.route('folder/:id', 'folder', function (id, params) {
    // Fetch the folder by id, then render the view.
    var folder = new FolderModel();
    folder.set({
        _id: id
    }).on('g:fetched', function () {
        Events.trigger('g:navigateTo', FolderView, _.extend({
            folder: folder,
            upload: params.dialog === 'upload',
            folderAccess: params.dialog === 'folderaccess',
            folderCreate: params.dialog === 'foldercreate',
            folderEdit: params.dialog === 'folderedit',
            itemCreate: params.dialog === 'itemcreate'
        }, params || {}));
    }, this).fetch();
});
