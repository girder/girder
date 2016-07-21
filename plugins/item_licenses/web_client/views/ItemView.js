import _ from 'underscore';

import ItemView from 'girder/views/body/ItemView';
import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

import ItemLicenseWidget from './ItemLicenseWidget';

/**
 * Show license on the item page.
 */
wrap(ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        var itemLicenseItemWidget = new ItemLicenseWidget({ // eslint-disable-line new-cap
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
        type: 'GET',
        path: 'item/licenses'
    }).done(_.bind(function (resp) {
        this.licenses = resp;
        editItem.call(this);
    }, this));

    return this;
});
