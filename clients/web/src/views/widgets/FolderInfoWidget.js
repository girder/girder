var MiscFunctions            = require('girder/utilities/MiscFunctions');
var FolderInfoDialogTemplate = require('girder/templates/widgets/folderInfoDialog.jade');
var View                     = require('girder/view');

require('girder/utilities/jQuery'); // $.girderModal

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

        this.$el.html(FolderInfoDialogTemplate({
            folder: this.model,
            MiscFunctions: MiscFunctions
        })).girderModal(this);
    }
});

module.exports = FolderInfoWidget;
