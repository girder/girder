import './routes.js';
import template from './templates/folderActions.pug';


const HierarchyWidget = girder.views.widgets.HierarchyWidget;
const { wrap } = girder.utilities.PluginUtils;
const { AccessType } = girder.constants;

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
