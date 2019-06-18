import $ from 'jquery';

import ItemView from '@girder/core/views/body/ItemView';
import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';

import ItemLicenseWidget from './ItemLicenseWidget';

/**
 * Show license on the item page.
 */
wrap(ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        var itemLicenseItemWidget = new ItemLicenseWidget({
            item: this.model,
            parentView: this
        }).render();

        $('.g-item-info').append(itemLicenseItemWidget.el);
    }, this);

    render.call(this);

    return this;
});

/**
 * Allow selecting license when editing an item.
 */
wrap(ItemView, 'editItem', function (editItem) {
    restRequest({
        method: 'GET',
        url: 'item/licenses'
    }).done((resp) => {
        this.licenses = resp;
        editItem.call(this);
    });

    return this;
});
