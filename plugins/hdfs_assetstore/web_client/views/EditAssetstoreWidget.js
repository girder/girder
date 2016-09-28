import EditAssetstoreWidget from 'girder/views/widgets/EditAssetstoreWidget';
import { AssetstoreType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import EditAssetstoreWidgetFieldsTemplate from '../templates/editAssetstoreWidgetFields.pug';

/**
 * Adds HDFS-specific fields to the edit dialog.
 */
wrap(EditAssetstoreWidget, 'render', function (render) {
    render.call(this);

    if (this.model.get('type') === AssetstoreType.HDFS) {
        this.$('.g-assetstore-form-fields').append(
            EditAssetstoreWidgetFieldsTemplate({
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
