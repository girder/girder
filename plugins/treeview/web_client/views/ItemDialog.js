import _ from 'underscore';

import TreeDialog from './TreeDialog';

const FolderDialog = TreeDialog.extend({
    initialize(settings = {}) {
        const treeviewSettings = _.defaults(
            settings.treeview || {},
            {
                selectable: ['item']
            }
        );

        settings.treeview = treeviewSettings;

        _.defaults(settings, {
            title: 'Select an item',
            placeholder: 'Click on an item to select it.'
        });

        return TreeDialog.prototype.initialize.apply(this, arguments);
    }
});

export default FolderDialog;
