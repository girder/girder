/**
 * Extends the core assetstore model to add HDFS-specific functionality.
 */
(function () {
    var prototype = girder.models.AssetstoreModel.prototype;

    prototype.hdfsImport = function (params) {
        girder.restRequest({
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
})();
