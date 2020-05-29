import $ from 'jquery';

import { AccessType } from '@girder/core/constants';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';
import MetadataWidget from '@girder/core/views/widgets/MetadataWidget';

import ItemTagsWidgetTemplate from '../templates/itemTagsWidget.pug';
import ItemTagsWidget from './ItemTagsWidget';

/** The key in the item metadata that item tags are saved under */
const METADATA_KEY = 'girder_item_tags';

/**
 * Saves the
 * Passed to ItemTagsWidget and called when a tag being edited is saved.
 */
const saveTags = function (tags) {
    tags = tags.filter(function (tag) {
        // filter out empty string tags
        return tag !== '';
    }).filter(function (item, pos, self) {
        // filter out duplicate tags
        return self.indexOf(item) === pos;
    }).sort(); // sort
    const successCallback = function () {
        this.itemTagsWidget.tags = tags;
        this.item.trigger('g:changed');
    };
    const errorCallback = function () {
        events.trigger('g:alert', {
            text: 'Failed to save tags',
            type: 'danger'
        });
    };
    this.item.editMetadata(METADATA_KEY, METADATA_KEY, tags, successCallback.bind(this), errorCallback.bind(this));
};

// Add the Item Tags widget before the Metadata widget
wrap(MetadataWidget, 'render', function (render) {
    render.call(this);
    // Only attach if it hasn't been attached yet
    // Only attach to items, not folders or collections
    if ($('.g-item-tags').length === 0 && this.item.attributes._modelType === 'item') {
        this.$el.before(ItemTagsWidgetTemplate({
            accessLevel: this.accessLevel,
            AccessType: AccessType
        }));
        restRequest({ url: 'resource/tags', method: 'GET' })
            .then((resp) => {
                this.itemTagsWidget = new ItemTagsWidget({
                    el: this.el.previousSibling,
                    tags: this.item.attributes.meta[METADATA_KEY] || [],
                    allowedTags: resp,
                    accessLevel: this.accessLevel,
                    parentView: this,
                    saveTags: saveTags.bind(this),
                    AccessType: AccessType
                });
                this.item.on('g:changed', function () {
                    this.itemTagsWidget.render();
                }, this);
                return true;
            });
    }
});
