import View from '@girder/core/views/View';
import { formatDate, DATE_SECOND, renderMarkdown, formatSize } from '@girder/core/misc';

import CollectionInfoDialogTemplate from '@girder/core/templates/widgets/collectionInfoDialog.pug';

import '@girder/core/utilities/jquery/girderModal';

/**
 * This view shows a dialog containing detailed collection information.
 */
var CollectionInfoWidget = View.extend({
    initialize: function () {
        this.needToFetch = !this.model.has('nFolders');
        if (this.needToFetch || this.timestamp !== this.model.get('updated')) {
            this.model.once('g:fetched.details', function () {
                this.needToFetch = false;
                this.timestamp = this.model.get('updated');
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

        return this;
    }
});

export default CollectionInfoWidget;
