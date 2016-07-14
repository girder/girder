/**
 * Item widget extensions for licenses.
 */
girder.views.item_licenses_ItemWidget = girder.View.extend({
    initialize: function (settings) {
        this.item = settings.item;
    },
    render: function () {
        this.$el.html(girder.templates.item_licenses_item({
            item: this.item
        }));
        return this;
    }
});

