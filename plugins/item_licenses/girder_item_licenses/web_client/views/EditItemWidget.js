import SelectLicenseWidget from './SelectLicenseWidget';

const $ = girder.$;
const _ = girder._;
const EditItemWidget = girder.views.widgets.EditItemWidget;
const { wrap } = girder.utilities.PluginUtils;

/**
 * Add select license widget to the edit item widget.
 */
wrap(EditItemWidget, 'render', function (render) {
    render.call(this);

    if (_.has(this.parentView, 'licenses')) {
        var currentLicense = null;
        if (this.item && this.item.has('license')) {
            currentLicense = this.item.get('license');
        }

        var selectLicenseWidget = new SelectLicenseWidget({
            licenses: this.parentView.licenses,
            currentLicense: currentLicense,
            parentView: this
        }).render();

        $('.modal-body > .form-group').last().after(selectLicenseWidget.el);

        delete this.parentView.licenses;
    }

    return this;
});

/**
 * Extend edit item widget to add license field when updating an item.
 */
wrap(EditItemWidget, 'updateItem', function (updateItem) {
    var fields = arguments[1];
    fields.license = this.$('#g-license').val();
    updateItem.call(this, fields);
    return this;
});

/**
 * Extend edit item widget to add license field when creating an item.
 */
wrap(EditItemWidget, 'createItem', function (createItem) {
    var fields = arguments[1];
    fields.license = this.$('#g-license').val();
    createItem.call(this, fields);
    return this;
});
