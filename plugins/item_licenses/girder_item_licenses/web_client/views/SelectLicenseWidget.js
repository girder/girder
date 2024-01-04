import SelectLicenseWidgetTemplate from '../templates/selectLicenseWidget.pug';

const View = girder.views.View;

/**
 * Widget that allows user to select a license.
 */
var SelectLicenseWidget = View.extend({
    initialize: function (settings) {
        this.licenses = settings.licenses;
        this.currentLicense = settings.currentLicense;
    },

    render: function () {
        this.$el.html(SelectLicenseWidgetTemplate({
            licenses: this.licenses,
            currentLicense: this.currentLicense
        }));
        return this;
    }
});

export default SelectLicenseWidget;
