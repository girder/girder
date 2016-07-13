/**
 * Widget that allows user to select a license.
 */
girder.views.item_licenses_SelectLicenseWidget = girder.View.extend({
    initialize: function (settings) {
        this.licenses = settings.licenses;
        this.currentLicense = settings.currentLicense;
    },

    render: function () {
        this.$el.html(girder.templates.item_licenses_selectLicense({
            licenses: this.licenses,
            currentLicense: this.currentLicense
        }));
        return this;
    }
});

