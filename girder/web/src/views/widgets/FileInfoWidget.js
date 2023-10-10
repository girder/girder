import View from '@girder/core/views/View';
import { formatDate, DATE_SECOND } from '@girder/core/misc';

import FileInfoDialogTemplate from '@girder/core/templates/widgets/fileInfoDialog.pug';

import '@girder/core/utilities/jquery/girderModal';

/**
 * This widget shows information about a single file in a modal dialog.
 */
var FileInfoWidget = View.extend({
    initialize: function (settings) {
        this.parentItem = settings.parentItem;
    },

    render: function () {
        this.$el.html(FileInfoDialogTemplate({
            file: this.model,
            formatDate: formatDate,
            DATE_SECOND: DATE_SECOND
        })).girderModal(this);
        return this;
    }
});

export default FileInfoWidget;
