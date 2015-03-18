girder.AssetstoreType.HDFS = 'hdfs';

/**
 * Adds HDFS-specific info and an import button to the assetstore list view.
 */
girder.wrap(girder.views.AssetstoresView, 'render', function (render) {
    render.call(this);

    var selector = '.g-assetstore-info-section[assetstore-type="' +
        girder.AssetstoreType.HDFS + '"]';

    _.each(this.$(selector), function (el) {
        var $el = $(el),
            assetstore = this.collection.get($el.attr('cid'));
        $el.append(girder.templates.hdfs_assetstore_info({
            assetstore: assetstore
        }));
        $el.parent().find('.g-assetstore-buttons').append(
            girder.templates.hdfs_assetstore_importButton({
                assetstore: assetstore
            })
        );
    }, this);

    this.$('.g-hdfs-import-button').tooltip({
        delay: 200
    });
});

/**
 * Add UI for creating new HDFS assetstore.
 */
girder.wrap(girder.views.NewAssetstoreWidget, 'render', function (render) {
    render.call(this);

    this.$('#g-assetstore-accordion').append(girder.templates.hdfs_assetstore_create());
});

girder.views.NewAssetstoreWidget.prototype.events['submit #g-new-hdfs-form'] = function (e) {
    this.createAssetstore(e, this.$('#g-new-hdfs-error'), {
        type: girder.AssetstoreType.HDFS,
        name: this.$('#g-new-hdfs-name').val(),
        path: this.$('#g-new-hdfs-path').val(),
        effectiveUser: this.$('#g-new-hdfs-user').val(),
        host: this.$('#g-new-hdfs-host').val(),
        port: this.$('#g-new-hdfs-port').val(),
        webHdfsPort: this.$('#g-new-webhdfs-port').val()
    });
};

/**
 * Adds HDFS-specific fields to the edit dialog.
 */
girder.wrap(girder.views.EditAssetstoreWidget, 'render', function (render) {
    render.call(this);

    if (this.model.get('type') === girder.AssetstoreType.HDFS) {
        this.$('.g-assetstore-form-fields').append(
            girder.templates.hdfs_assetstore_editFields({
                assetstore: this.model
            })
        );
    }
});

girder.views.EditAssetstoreWidget.prototype.fieldsMap.hdfs = {
    get: function () {
        return {
            hdfsHost: this.$('#g-edit-hdfs-host').val(),
            hdfsPort: this.$('#g-edit-hdfs-port').val(),
            webHdfsPort: this.$('#g-edit-webhdfs-port').val(),
            hdfsPath: this.$('#g-edit-hdfs-path').val(),
            hdfsUser: this.$('#g-edit-hdfs-user').val()
        };
    },
    set: function () {
        var hdfsInfo = this.model.get('hdfs');
        this.$('#g-edit-hdfs-host').val(hdfsInfo.host);
        this.$('#g-edit-hdfs-port').val(hdfsInfo.port);
        this.$('#g-edit-webhdfs-port').val(hdfsInfo.webHdfsPort);
        this.$('#g-edit-hdfs-path').val(hdfsInfo.path);
        this.$('#g-edit-hdfs-user').val(hdfsInfo.user);
    }
};
