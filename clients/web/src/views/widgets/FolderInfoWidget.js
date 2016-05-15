var girder = require('girder/init');
var View   = require('girder/view');

/**
 * This view shows a dialog container detailed folder information.
 */
var FolderInfoWidget = View.extend({
    initialize: function () {
        this.needToFetch = !this.model.has('nItems') || !this.model.has('nFolders');
        if (this.needToFetch) {
            this.model.fetch({extraPath: 'details'}).once('g:fetched.details', function () {
                this.needToFetch = false;
                this.render();
            }, this);
        }
    },

    render: function () {
        if (this.needToFetch) {
            return;
        }

        this.$el.html(girder.templates.folderInfoDialog({
            folder: this.model,
            girder: girder
        })).girderModal(this);
    }
});

module.exports = FolderInfoWidget;
