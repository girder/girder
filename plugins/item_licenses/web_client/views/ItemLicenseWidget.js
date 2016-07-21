import View from 'girder/views/View';

import ItemLicenseWidgetTemplate from '../templates/itemLicenseWidget.jade';

/**
 * Item widget extensions for licenses.
 */
var ItemLicenseWidget = View.extend({
    initialize: function (settings) {
        this.item = settings.item;
    },
    render: function () {
        this.$el.html(ItemLicenseWidgetTemplate({
            item: this.item
        }));
        return this;
    }
});

export default ItemLicenseWidget;
