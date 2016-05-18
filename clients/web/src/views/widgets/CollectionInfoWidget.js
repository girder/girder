var CollectionInfoDialogTemplate = require('girder/templates/widgets/collectionInfoDialog.jade');
var MiscFunctions                = require('girder/utilities/MiscFunctions');
var View                         = require('girder/view');

require('girder/utilities/jQuery'); // $.girderModal

/**
 * This view shows a dialog containing detailed collection information.
 */
var CollectionInfoWidget = View.extend({
    initialize: function () {
        this.needToFetch = !this.model.has('nFolders');
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

        this.$el.html(CollectionInfoDialogTemplate({
            collection: this.model,
            MiscFunctions: MiscFunctions
        })).girderModal(this);
    }
});

module.exports = CollectionInfoWidget;
