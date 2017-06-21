import $ from 'jquery';

import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import { wrap } from 'girder/utilities/PluginUtils';

import ItemPreviewWidget from './ItemPreviewWidget';

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);
    if (this.parentModel.resourceName === 'folder' && this._showItems) {
        var $element = $('<div class="g-item-previews-container">');
        this.$el.append($element);
        this.itemPreviewView.setElement($element);
        this.itemPreviewView.setCollection(this.itemListView.collection);
        this.itemPreviewView.render();
    }

    return this;
});

wrap(HierarchyWidget, '_initFolderViewSubwidgets', function (base) {
    base.call(this);
    if (this._showItems && !this.itemPreviewView) {
        this.itemPreviewView = new ItemPreviewWidget({
            collection: this.itemListView.collection,
            parentView: this
        });
    }

    return this;
});
