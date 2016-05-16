var girder = require('girder/init');
var View   = require('girder/view');

var CollectionInfoDialogTemplate = require('girder/templates/widgets/collectionInfoDialog.jade');

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
            girder: girder
        })).girderModal(this);
    }
});

module.exports = CollectionInfoWidget;
