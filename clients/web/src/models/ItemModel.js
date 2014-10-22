girder.models.ItemModel = girder.Model.extend({
    resourceName: 'item',

    /**
     * Get the access level of the item and pass it to the callback
     * function passed in as a parameter.
     */
    getAccessLevel: function (callback) {
        if (this.parent && this.parent.getAccessLevel()) {
            callback(this.parent.getAccessLevel());
        } else {
            this.parent = new girder.models.FolderModel();
            this.parent.set({
                _id: this.get('folderId')
            }).on('g:fetched', function () {
                callback(this.parent.getAccessLevel());
            }, this).fetch();
        }
    },

    /**
     * Get the path to the root of the hierarchy
     */
    getRootPath: function (callback) {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/rootpath'
        }).done(_.bind(function (resp) {
            callback(resp);
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    }
});

_.extend(girder.models.ItemModel.prototype, girder.models.MetadataMixin);
