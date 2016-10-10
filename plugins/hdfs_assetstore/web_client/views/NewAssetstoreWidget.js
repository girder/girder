import NewAssetstoreWidget from 'girder/views/widgets/NewAssetstoreWidget';
import { AssetstoreType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import NewAssetstoreWidgetCreateTemplate from '../templates/newAssetstoreWidgetCreate.pug';

/**
 * Add UI for creating new HDFS assetstore.
 */
wrap(NewAssetstoreWidget, 'render', function (render) {
    render.call(this);

    this.$('#g-assetstore-accordion').append(NewAssetstoreWidgetCreateTemplate());
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
