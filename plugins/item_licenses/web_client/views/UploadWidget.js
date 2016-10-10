import _ from 'underscore';

import ItemModel from 'girder/models/ItemModel';
import UploadWidget from 'girder/views/widgets/UploadWidget';
import { wrap } from 'girder/utilities/PluginUtils';

import SelectLicenseWidget from './SelectLicenseWidget';

/**
 * Add select license widget to the upload widget.
 */
wrap(UploadWidget, 'render', function (render) {
    render.call(this);

    if (_.has(this.parentView, 'licenses')) {
        this.selectLicenseWidget = new SelectLicenseWidget({ // eslint-disable-line new-cap
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
