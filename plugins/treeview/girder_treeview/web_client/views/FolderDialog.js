import _ from 'underscore';

import TreeDialog from './TreeDialog';

/**
 * This view is a modal dialog for selecting folders.
 */
const FolderDialog = TreeDialog.extend({
    initialize(settings = {}) {
        const treeviewSettings = _.defaults(
            settings.treeview || {},
            {
                selectable: ['folder']
            }
        );

        settings.treeview = treeviewSettings;

        _.defaults(settings, {
            title: 'Select a folder',
            placeholder: 'Click on a folder to select it.'
        });

        return TreeDialog.prototype.initialize.apply(this, arguments);
    }
});

export default FolderDialog;
