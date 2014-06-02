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
     * Get the path to the root of the hierarcy
     */
    getRootPath: function (callback) {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/rootpath'
        }).done(_.bind(function (resp) {
            callback(resp);
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    _sendMetadata: function (metadata, successCallback, errorCallback) {
        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/metadata',
            contentType: 'application/json',
            data: JSON.stringify(metadata),
            type: 'PUT',
            error: null
        }).done(_.bind(function (resp) {
            this.set('meta', resp.meta);
            successCallback();
        }, this)).error(_.bind(function (err) {
            err.message = err.responseJSON.message;
            errorCallback(err);
        }, this));
    },

    addMetadata: function (key, value, successCallback, errorCallback) {
        var datum = {};
        datum[key] = value;
        var meta = this.get('meta');
        if (meta && key in meta) {
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
