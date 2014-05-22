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

    _sendMetadata: function (metadata, callback) {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/metadata',
            contentType: 'application/json',
            data: JSON.stringify(metadata),
            type: 'PUT',
            error: null
        }).done(_.bind(function (resp) {
            callback();
        }, this)).error(_.bind(function (err) {
            console.log(err);
        }, this));
    },

    addMetadata: function (key, value, callback) {
        var datum = {};
        datum[key] = value;
        this._sendMetadata(datum, callback);
    },

    removeMetadata: function (key, callback) {
        this.addMetadata(key, null, callback);
    },

    editMetadata: function(newKey, oldKey, value, callback) {
        if (newKey === oldKey) {
            this.addMetadata(newKey, value, callback);
        } else {
            var metas = {};
            metas[oldKey] = null;
            metas[newKey] = value;
            this._sendMetadata(metas, callback);
        }
    }

});
