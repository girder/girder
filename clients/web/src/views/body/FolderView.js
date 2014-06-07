/**
 * This view shows a single folder as a hierarchy widget.
 */
girder.views.FolderView = girder.View.extend({
    initialize: function (settings) {
        this.folder = settings.folder;
        this.render();
    },

    render: function () {
        this.hierarchyWidget = new girder.views.HierarchyWidget({
            parentModel: this.folder,
            el: this.$el
        });

        return this;
    }
});

girder.router.route('folder/:id', 'folder', function (id) {
    // Fetch the folder by id, then render the view.
    var folder = new girder.models.FolderModel();
    folder.set({
        _id: id
    }).on('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.FolderView, {
            folder: folder
        });
    }, this).on('g:error', function () {
        girder.router.navigate('collections', {trigger: true});
    }, this).fetch();
});
