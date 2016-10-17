import './routes.js';

import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import { AccessType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import template from './templates/folderActions.pug';

// Add an entry to create an authorized upload in the hierarchy widget folder menu
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder' &&
            this.parentModel.getAccessLevel() >= AccessType.WRITE) {
        this.$('.g-folder-actions-menu a.g-edit-folder').parent().after(template({
            folder: this.parentModel
        }));
    }
    return this;
});
