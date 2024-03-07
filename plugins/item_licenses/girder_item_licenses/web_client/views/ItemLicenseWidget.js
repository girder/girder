import ItemLicenseWidgetTemplate from '../templates/itemLicenseWidget.pug';

const View = girder.views.View;

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
