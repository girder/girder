/**
 * This widget shows information about a single file in a modal dialog.
 */
girder.views.FileInfoWidget = girder.View.extend({
    render: function () {
        this.$el.html(girder.templates.fileInfoDialog({
            file: this.model,
            girder: girder
        })).girderModal(this);
    }
});
