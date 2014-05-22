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

    _sendMetadata: function (metadata, successCallback, errorCallback) {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/metadata',
            contentType: 'application/json',
            data: JSON.stringify(metadata),
            type: 'PUT',
            error: null
        }).done(_.bind(function (resp) {
            successCallback();
        }, this)).error(_.bind(function (err) {
            err.message = err.responseJSON.message;
            errorCallback(err);
        }, this));
    },

    addMetadata: function (key, value, successCallback, errorCallback) {
        var datum = {};
        datum[key] = value;
        if (key in this.get('meta')) {
            errorCallback({message: key + ' is already a metadata key'});
            return;
        }
        this._sendMetadata(datum, successCallback, errorCallback);
    },

    removeMetadata: function (key, successCallback, errorCallback) {
        var datum = {};
        datum[key] = null;
        this._sendMetadata(datum, successCallback, errorCallback);
    },

    editMetadata: function (newKey, oldKey, value, successCallback, errorCallback) {
        if (newKey === oldKey) {
            var datum = {};
            datum[newKey] = value;
            this._sendMetadata(datum, successCallback, errorCallback);
        } else {
            if (newKey in this.get('meta')) {
                errorCallback({message: newKey + ' is already a metadata key'});
                return;
            }
            var metas = {};
            metas[oldKey] = null;
            metas[newKey] = value;
            this._sendMetadata(metas, successCallback, errorCallback);
        }
    }

});
