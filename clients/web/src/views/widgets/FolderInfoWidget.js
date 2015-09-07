/**
 * This view allows users to see and control access on a resource.
 */
girder.views.FolderInfoWidget = girder.View.extend({
    events: {

    },

    initialize: function (settings) {
        if (!this.model.has('nItems')) {
            this.model.fetch({extraPath: 'details'}).once('g:fetched', function () {
            }, this);
        }
    },

    render: function () {
        this.$el.html(girder.templates.folderInfoDialog({
            folder: this.model,
            girder: girder
        })).girderModal(this);
    }
});
