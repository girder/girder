// Add create thumbnail link to each file in the file list
girder.wrap(girder.views.FileListWidget, 'render', function (render) {
    render.call(this);

    if (this.parentItem.getAccessLevel() >= girder.AccessType.WRITE) {
        this.$('.g-file-actions-container').prepend(girder.templates.thumbnails_createButton());
        this.$('.g-create-thumbnail').tooltip({
            container: 'body',
            placement: 'auto',
            delay: 100
        });
    }

    return this;
});

// Bind the thumbnail creation button
girder.views.FileListWidget.prototype.events['click a.g-create-thumbnail'] = function (e) {
    var cid = $(e.currentTarget).parent().attr('file-cid');

    new girder.views.thumbnails_CreateThumbnailView({
        el: $('#g-dialog-container'),
        parentView: this,
        item: this.parentItem,
        file: this.collection.get(cid)
    }).once('g:created', function (params) {
        Backbone.history.fragment = null;
        girder.router.navigate(params.attachedToType + '/' + params.attachedToId, {trigger: true});
    }, this).render();
};
