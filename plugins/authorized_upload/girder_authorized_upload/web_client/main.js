import './routes.js';
import template from './templates/folderActions.pug';


const HierarchyWidget = girder.views.widgets.HierarchyWidget;
const { wrap } = girder.utilities.PluginUtils;
const { AccessType } = girder.constants;
const { isHtkStyle } = girder.uiStyle;

// Add an entry to create an authorized upload in the hierarchy widget folder menu
wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.resourceName === 'folder' &&
            this.parentModel.getAccessLevel() >= AccessType.WRITE) {
        const entry = template({
            folder: this.parentModel,
            htk: isHtkStyle()
        });
        const editFolder = this.$('.g-folder-actions-menu a.g-edit-folder');
        if (isHtkStyle()) {
            // The htk menu holds its links directly rather than in list items
            editFolder.after(entry);
        } else {
            editFolder.parent().after(entry);
        }
    }
    return this;
});
