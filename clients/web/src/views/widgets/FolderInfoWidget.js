import View from 'girder/views/View';
import { formatDate, formatSize, DATE_SECOND, renderMarkdown } from 'girder/utilities/MiscFunctions';

import FolderInfoDialogTemplate from 'girder/templates/widgets/folderInfoDialog.jade';

import 'bootstrap/js/modal';
import 'girder/utilities/JQuery'; // $.girderModal

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
            formatDate: formatDate,
            formatSize: formatSize,
            renderMarkdown: renderMarkdown,
            DATE_SECOND: DATE_SECOND
        })).girderModal(this);
    }
});

export default FolderInfoWidget;
