/**
 * Show license on the item page.
 */
girder.wrap(girder.views.ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        var itemLicenseItemWidget = new girder.views.item_licenses_ItemWidget({ // eslint-disable-line new-cap
            item: this.model,
            parentView: this
        }).render();

        $('.g-item-info').append(itemLicenseItemWidget.el);
    }, this);

    render.call(this);

    return this;
});

/**
 * Allow selecting license when uploading an item.
 */
girder.wrap(girder.views.HierarchyWidget, 'uploadDialog', function (uploadDialog) {
    girder.restRequest({
        type: 'GET',
        path: 'item/licenses'
    }).done(_.bind(function (resp) {
        this.licenses = resp;
        uploadDialog.call(this);
    }, this));

    return this;
});

/**
 * Add select license widget to the upload widget.
 */
girder.wrap(girder.views.UploadWidget, 'render', function (render) {
    render.call(this);

    if (_.has(this.parentView, 'licenses')) {
        this.selectLicenseWidget = new girder.views.item_licenses_SelectLicenseWidget({ // eslint-disable-line new-cap
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
girder.wrap(girder.views.UploadWidget, 'uploadNextFile', function (uploadNextFile) {
    uploadNextFile.call(this);

    if (_.has(this, 'selectLicenseWidget')) {
        var file = this.currentFile;
        if (file) {
            file.on('g:upload.complete', function () {
                var license = $('#g-license').val();
                if (!_.isEmpty(license)) {
                    var item = new girder.models.ItemModel({
                        _id: file.get('itemId'),
                        license: license
                    });
                    item.save();
                }
            }, this);
        }
    }
});

/**
 * Allow selecting license when creating an item.
 */
girder.wrap(girder.views.HierarchyWidget, 'createItemDialog', function (createItemDialog) {
    girder.restRequest({
        type: 'GET',
        path: 'item/licenses'
    }).done(_.bind(function (resp) {
        this.licenses = resp;
        createItemDialog.call(this);
    }, this));

    return this;
});

/**
 * Allow selecting license when editing an item.
 */
girder.wrap(girder.views.ItemView, 'editItem', function (editItem) {
    girder.restRequest({
        type: 'GET',
        path: 'item/licenses'
    }).done(_.bind(function (resp) {
        this.licenses = resp;
        editItem.call(this);
    }, this));

    return this;
});

/**
 * Add select license widget to the edit item widget.
 */
girder.wrap(girder.views.EditItemWidget, 'render', function (render) {
    render.call(this);

    if (_.has(this.parentView, 'licenses')) {
        var currentLicense = null;
        if (this.item && this.item.has('license')) {
            currentLicense = this.item.get('license');
        }

        var selectLicenseWidget = new girder.views.item_licenses_SelectLicenseWidget({ // eslint-disable-line new-cap
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
girder.wrap(girder.views.EditItemWidget, 'updateItem', function (updateItem) {
    var fields = arguments[1];
    fields['license'] = this.$('#g-license').val();
    updateItem.call(this, fields);
    return this;
});

/**
 * Extend edit item widget to add license field when creating an item.
 */
girder.wrap(girder.views.EditItemWidget, 'createItem', function (createItem) {
    var fields = arguments[1];
    fields['license'] = this.$('#g-license').val();
    createItem.call(this, fields);
    return this;
});

/**
 * Register plugin configuration page.
 */
girder.exposePluginConfig('item_licenses', 'plugins/item_licenses/config');
