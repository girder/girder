import _ from 'underscore';

import AssetstoresView from 'girder/views/body/AssetstoresView';
import { AssetstoreType } from 'girder/constants';
import { wrap } from 'girder/utilities/PluginUtils';

import AssetstoresViewInfoTemplate from '../templates/assetstoresViewInfo.pug';
import AssetstoresViewImportButtonTemplate from '../templates/assetstoresViewImportButton.pug';

/**
 * Adds HDFS-specific info and an import button to the assetstore list view.
 */
wrap(AssetstoresView, 'render', function (render) {
    render.call(this);

    var selector = '.g-assetstore-info-section[assetstore-type="' + AssetstoreType.HDFS + '"]';

    _.each(this.$(selector), function (el) {
        var $el = $(el),
            assetstore = this.collection.get($el.attr('cid'));
        $el.append(AssetstoresViewInfoTemplate({
            assetstore: assetstore
        }));
        $el.parent().find('.g-assetstore-buttons').append(
            AssetstoresViewImportButtonTemplate({
                assetstore: assetstore
            })
        );
    }, this);

    this.$('.g-hdfs-import-button').tooltip({
        delay: 200
    });
});
