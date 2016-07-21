import View from 'girder/views/View';
import { formatDate, DATE_SECOND } from 'girder/utilities/MiscFunctions';

import FileInfoDialogTemplate from 'girder/templates/widgets/fileInfoDialog.jade';

import 'bootstrap/js/modal';
import 'girder/utilities/JQuery'; // $.girderModal

/**
 * This widget shows information about a single file in a modal dialog.
 */
var FileInfoWidget = View.extend({
    render: function () {
        this.$el.html(FileInfoDialogTemplate({
            file: this.model,
            formatDate: formatDate,
            DATE_SECOND: DATE_SECOND
        })).girderModal(this);
    }
});

export default FileInfoWidget;
