import View from '@girder/core/views/View';
import { formatDate, formatSize, DATE_SECOND, renderMarkdown } from '@girder/core/misc';

import FolderInfoDialogTemplate from '@girder/core/templates/widgets/folderInfoDialog.pug';

import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a dialog container detailed folder information.
 */
var FolderInfoWidget = View.extend({
    initialize: function () {
        this.needToFetch = !this.model.has('nItems') || !this.model.has('nFolders');
        if (this.needToFetch) {
            this.model.once('g:fetched.details', function () {
                this.needToFetch = false;
                this.render();
            }, this).fetch({ extraPath: 'details' });
        }
    },

    render: function () {
        if (this.needToFetch) {
            return this;
        }

        this.$el.html(FolderInfoDialogTemplate({
            folder: this.model,
            formatDate: formatDate,
            formatSize: formatSize,
            renderMarkdown: renderMarkdown,
            DATE_SECOND: DATE_SECOND
        })).girderModal(this);

        return this;
    }
});

export default FolderInfoWidget;
