import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';

/**
 * Allow selecting license when uploading an item.
 */
wrap(HierarchyWidget, 'uploadDialog', function (uploadDialog) {
    restRequest({
        method: 'GET',
        url: 'item/licenses'
    }).done((resp) => {
        this.licenses = resp;
        uploadDialog.call(this);
    });

    return this;
});

/**
 * Allow selecting license when creating an item.
 */
wrap(HierarchyWidget, 'createItemDialog', function (createItemDialog) {
    restRequest({
        method: 'GET',
        url: 'item/licenses'
    }).done((resp) => {
        this.licenses = resp;
        createItemDialog.call(this);
    });

    return this;
});
