import View from 'girder/views/View';
import { formatDate, DATE_SECOND, renderMarkdown, formatSize } from 'girder/misc';

import CollectionInfoDialogTemplate from 'girder/templates/widgets/collectionInfoDialog.pug';

import 'girder/utilities/jquery/girderModal';

/**
 * This view shows a dialog containing detailed collection information.
 */
var CollectionInfoWidget = View.extend({
    initialize: function () {
        this.needToFetch = !this.model.has('nFolders');
        if (this.needToFetch) {
            this.model.once('g:fetched.details', function () {
                this.needToFetch = false;
                this.render();
            }, this).fetch({extraPath: 'details'});
        }
    },

    render: function () {
        if (this.needToFetch) {
            return;
        }

        this.$el.html(CollectionInfoDialogTemplate({
            collection: this.model,
            formatDate: formatDate,
            formatSize: formatSize,
            DATE_SECOND: DATE_SECOND,
            renderMarkdown: renderMarkdown
        })).girderModal(this);
    }
});

export default CollectionInfoWidget;
