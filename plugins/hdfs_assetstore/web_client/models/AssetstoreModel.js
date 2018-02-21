import AssetstoreModel from 'girder/models/AssetstoreModel';
import { restRequest } from 'girder/rest';

/**
 * Extends the core assetstore model to add HDFS-specific functionality.
 */
AssetstoreModel.hdfsImport = function (params) {
    restRequest({
        url: `hdfs_assetstore/${this.id}/import`,
        method: 'PUT',
        data: params,
        error: null
    }).done(() => {
        this.trigger('g:imported');
    }).fail((err) => {
        this.trigger('g:error', err);
    });

    return this;
};

export default AssetstoreModel;
