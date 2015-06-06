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

// Show thumbnails on the item page
girder.wrap(girder.views.ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        var thumbnails = _.map(this.model.get('_thumbnails'), function (id) {
            return new girder.models.FileModel({_id: id});
        });

        if (thumbnails && thumbnails.length) {
            var el = $('<div>', {
                class: 'g-thumbnails-flow-view-container'
            }).prependTo(this.$('.g-item-info'));

            new girder.views.thumbnails_FlowView({
                parentView: this,
                thumbnails: thumbnails,
                accessLevel: this.model.getAccessLevel(),
                el: el
            }).render();

            var headerEl = $('<div>', {
                class: 'g-thumbnails-header-container'
            }).prependTo(this.$('.g-item-info'));

            headerEl.html(girder.templates.thumbnails_itemHeader());
        }
    }, this);

    render.call(this);
});
