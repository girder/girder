import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import { wrap } from 'girder/utilities/PluginUtils';

import ItemPreviewWidget from './ItemPreviewWidget';

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    // Only on folder views:
    if (this.parentModel.resourceName === 'folder' && this._showItems) {
        // Add the item preview widget into the container.
        this.itemPreviewView = new ItemPreviewWidget({
            className: 'g-item-previews-container',
            folderId: this.parentModel.get('_id'),
            parentView: this
        }).render();
        this.itemPreviewView.$el.appendTo(this.$el);
    }

    return this;
});
