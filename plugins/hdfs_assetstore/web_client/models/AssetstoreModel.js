import _ from 'underscore';

import AssetstoreModel from 'girder/models/AssetstoreModel';
import { restRequest } from 'girder/rest';

/**
 * Extends the core assetstore model to add HDFS-specific functionality.
 */
AssetstoreModel.hdfsImport = function (params) {
    restRequest({
        path: 'hdfs_assetstore/' + this.get('_id') + '/import',
        type: 'PUT',
        data: params,
        error: null
    }).done(_.bind(function () {
        this.trigger('g:imported');
    }, this)).error(_.bind(function (err) {
        this.trigger('g:error', err);
    }, this));

    return this;
};

export default AssetstoreModel;
