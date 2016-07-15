import _ from 'underscore';

import { wrap } from 'girder/utilities/PluginUtils';
import { AssetstoreType } from 'girder/constants';

AssetstoreType.HDFS = 'hdfs';

/**
 * Adds HDFS-specific info and an import button to the assetstore list view.
 */
import AssetstoresView from 'girder/views/body/AssetstoresView';
import InfoTemplate from './templates/info.jade';
import ImportButtonTemplate from './templates/importButton.jade';
wrap(AssetstoresView, 'render', function (render) {
    render.call(this);

    var selector = '.g-assetstore-info-section[assetstore-type="' + AssetstoreType.HDFS + '"]';

    _.each(this.$(selector), function (el) {
        var $el = $(el),
            assetstore = this.collection.get($el.attr('cid'));
        $el.append(InfoTemplate({
            assetstore: assetstore
        }));
        $el.parent().find('.g-assetstore-buttons').append(
            ImportButtonTemplate({
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
import NewAssetstoreWidget from 'girder/views/widgets/NewAssetstoreWidget';
import CreateTemplate from './templates/create.jade';
wrap(NewAssetstoreWidget, 'render', function (render) {
    render.call(this);

    this.$('#g-assetstore-accordion').append(CreateTemplate());
});

NewAssetstoreWidget.prototype.events['submit #g-new-hdfs-form'] = function (e) {
    this.createAssetstore(e, this.$('#g-new-hdfs-error'), {
        type: AssetstoreType.HDFS,
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
import EditAssetstoreWidget from 'girder/views/widgets/EditAssetstoreWidget';
import EditFieldsTemplate from './templates/editFields.jade';
wrap(EditAssetstoreWidget, 'render', function (render) {
    render.call(this);

    if (this.model.get('type') === AssetstoreType.HDFS) {
        this.$('.g-assetstore-form-fields').append(
            EditFieldsTemplate({
                assetstore: this.model
            })
        );
    }
});

EditAssetstoreWidget.prototype.fieldsMap.hdfs = {
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
