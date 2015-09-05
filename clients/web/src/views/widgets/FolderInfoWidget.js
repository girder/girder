/**
 * This view allows users to see and control access on a resource.
 */
girder.views.FolderInfoWidget = girder.View.extend({
    events: {

    },

    initialize: function (settings) {
        console.log(this.model);
    },

    render: function () {
        this.$el.html(girder.templates.folderInfoDialog({
            folder: this.model,
            girder: girder
        })).girderModal(this);
    }
});
