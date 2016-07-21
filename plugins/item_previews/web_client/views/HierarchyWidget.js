import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import { wrap } from 'girder/utilities/PluginUtils';

import ItemPreviewWidget from './ItemPreviewWidget';

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    // Only on folder views:
    if (this.parentModel.resourceName === 'folder' && this._showItems) {
        // Add the item-previews-container.
        var element = $('<div class="g-item-previews-container">');
        this.$el.append(element);

        // Add the item preview widget into the container.
        this.itemPreviewView = new ItemPreviewWidget({
            folderId: this.parentModel.get('_id'),
            parentView: this,
            el: element
        })
        .render();
    }

    return this;
});
