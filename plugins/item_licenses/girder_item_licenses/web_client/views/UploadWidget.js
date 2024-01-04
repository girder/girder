
import SelectLicenseWidget from './SelectLicenseWidget';

const $ = girder.$;
const _ = girder._;
const ItemModel = girder.models.ItemModel;
const UploadWidget = girder.views.widgets.UploadWidget;
const { wrap } = girder.utilities.PluginUtils;

/**
 * Add select license widget to the upload widget.
 */
wrap(UploadWidget, 'render', function (render) {
    render.call(this);

    if (_.has(this.parentView, 'licenses')) {
        this.selectLicenseWidget = new SelectLicenseWidget({
            licenses: this.parentView.licenses,
            parentView: this
        }).render();

        if (this.modal) {
            $('.modal-body').append(this.selectLicenseWidget.el);
        } else {
            $('.g-nonmodal-upload-buttons-container').before(this.selectLicenseWidget.el);
        }

        delete this.parentView.licenses;
    }

    return this;
});

/**
 * Set item license when file upload is complete.
 */
wrap(UploadWidget, 'uploadNextFile', function (uploadNextFile) {
    uploadNextFile.call(this);

    if (_.has(this, 'selectLicenseWidget')) {
        var file = this.currentFile;
        if (file) {
            file.on('g:upload.complete', function () {
                var license = $('#g-license').val();
                if (!_.isEmpty(license)) {
                    var item = new ItemModel({
                        _id: file.get('itemId'),
                        license: license
                    });
                    item.save();
                }
            }, this);
        }
    }
});
