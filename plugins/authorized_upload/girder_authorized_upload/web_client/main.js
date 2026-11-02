import './routes.js';

import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import { AccessType } from '@girder/core/constants';
import { wrap } from '@girder/core/utilities/PluginUtils';

import template from './templates/folderActions.pug';

// Add an entry to create an authorized upload in the hierarchy widget folder menu
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder' &&
            this.parentModel.getAccessLevel() >= AccessType.WRITE) {
        const editFolder = this.$('.g-folder-actions-menu a.g-edit-folder');
        // The classic menu wraps each link in a list item; the htk menu holds
        // its links directly
        const legacyMenu = editFolder.parent().is('li');
        const entry = template({ folder: this.parentModel, legacyMenu });
        if (legacyMenu) {
            editFolder.parent().after(entry);
        } else {
            editFolder.after(entry);
        }
    }
    return this;
});
