import _ from 'underscore';

import TreeDialog from './TreeDialog';

/**
 * This view is modal dialog for selecting files.
 */
const FolderDialog = TreeDialog.extend({
    initialize(settings = {}) {
        const treeviewSettings = _.defaults(
            settings.treeview || {},
            {
                selectable: ['file']
            }
        );

        settings.treeview = treeviewSettings;

        _.defaults(settings, {
            title: 'Select a file',
            placeholder: 'Click on a file to select it.'
        });

        return TreeDialog.prototype.initialize.apply(this, arguments);
    }
});

export default FolderDialog;
