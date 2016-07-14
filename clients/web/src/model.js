/**
 * All models should descend from this base model, which provides a number
 * of utilities for synchronization.
 */
girder.Model = Backbone.Model.extend({
    resourceName: null,
    altUrl: null,
    idAttribute: '_id',

    /**
     * Convenience method for incrementing numeric properties.
     * @param {string} attr The attribute to increment.
     * @param {number} [amount] The amount to increment by. Defaults to 1.
     */
    increment: function (attr, amount) {
        if (amount === undefined) {
            amount = 1;
        }
        if (!amount) {
            return;
        }
        return this.set(attr, this.get(attr) + amount);
    },

    /**
     * Get the name for this resource. By default, just the name attribute.
     */
    name: function () {
        return this.get('name');
    },

    /**
     * Save this model to the server. If this is a new model, meaning it has no
     * _id attribute, this will create it. If the _id is set, we update the
     * existing model. Triggers g:saved on success, and g:error on error.
     */
    save: function () {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or resourceName on your model.');
            return;
        }

        var path, type;
        if (this.has('_id')) {
            path = (this.altUrl || this.resourceName) + '/' + this.get('_id');
            type = 'PUT';
        } else {
            path = (this.altUrl || this.resourceName);
            type = 'POST';
        }
        /* Don't save attributes which are objects using this call.  For
         * instance, if the metadata of an item has keys that contain non-ascii
         * values, they won't get handled the the rest call. */
        var data = {};
        _.each(this.keys(), function (key) {
            var value = this.get(key);
            if (!_.isObject(value)) {
                data[key] = value;
            }
        }, this);

        girder.restRequest({
            path: path,
            type: type,
            data: data,
            error: null // don't do default error behavior (validation may fail)
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:saved');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Fetch a single resource from the server. Triggers g:fetched on success,
     * or g:error on error.
     * To ignore the default error handler, pass
     *     ignoreError: true
     * in your opts object.
     */
    fetch: function (opts) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        opts = opts || {};
        var restOpts = {
            path: (this.altUrl || this.resourceName) + '/' + this.get('_id')
        };
        if (opts.extraPath) {
            restOpts.path += '/' + opts.extraPath;
        }
        if (opts.ignoreError) {
            restOpts.error = null;
        }
        girder.restRequest(restOpts).done(_.bind(function (resp) {
            this.set(resp);
            if (opts.extraPath) {
                this.trigger('g:fetched.' + opts.extraPath);
            } else {
                this.trigger('g:fetched');
            }
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Get the path for downloading this resource via the API. Can be used
     * as the href property of a direct download link.
     * @param params {Object} list of key-value parameters to include in the
     *    query string.
     */
    downloadUrl: function (params) {
        var url = girder.apiRoot + '/' + (this.altUrl || this.resourceName) + '/' +
            this.get('_id') + '/download';

        if (params) {
            url += '?' + $.param(params);
        }

        return url;
    },

    /**
     * For models that can be downloaded, this method can be used to
     * initiate the download in the browser.
     */
    download: function () {
        window.location.assign(this.downloadUrl());
    },

    /**
     * Delete the model on the server.
     * @param opts Options, may contain:
     *   throwError Whether to throw an error (bool, default=true)
     *   progress Whether to record progress (bool, default=false)
     */
    destroy: function (opts) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        var args = {
            path: (this.altUrl || this.resourceName) + '/' + this.get('_id'),
            type: 'DELETE'
        };

        opts = opts || {};
        if (opts.progress === true) {
            args.path += '?progress=true';
        }

        if (opts.throwError !== false) {
            args.error = null;
        }

        girder.restRequest(args).done(_.bind(function () {
            if (this.collection) {
                this.collection.remove(this);
            }
            this.trigger('g:deleted');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Return the access level with respect to the current user
     */
    getAccessLevel: function () {
        return this.get('_accessLevel');
    }

});

/**
 * Models corresponding to AccessControlledModels on the server should extend
 * from this object. It provides utilities for managing and storing the
 * access control list on
 */
girder.AccessControlledModel = girder.Model.extend({
    /**
     * Saves the access control list on this model to the server. Saves the
     * state of whatever this model's "access" parameter is set to, which
     * should be an object of the form:
     *    {groups: [{id: <groupId>, level: <accessLevel>}, ...],
     *     users: [{id: <userId>, level: <accessLevel>}, ...]}
     * The "public" attribute of this model should also be set as a boolean.
     * When done, triggers the 'g:accessListSaved' event on the model.
     */
    updateAccess: function (params) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        girder.restRequest({
            path: (this.altUrl || this.resourceName) + '/' + this.get('_id') + '/access',
            type: 'PUT',
            data: _.extend({
                access: JSON.stringify(this.get('access')),
                public: this.get('public')
            }, params || {})
        }).done(_.bind(function () {
            this.trigger('g:accessListSaved');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Fetches the access control list from the server, and sets it as the
     * access property.
     * @param force By default, this only fetches access if it hasn't already
     *              been set on the model. If you want to force a refresh
     *              anyway, set this param to true.
     */
    fetchAccess: function (force) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        if (!this.get('access') || force) {
            girder.restRequest({
                path: (this.altUrl || this.resourceName) + '/' + this.get('_id') + '/access',
                type: 'GET'
            }).done(_.bind(function (resp) {
                if (resp.access) {
                    this.set(resp);
                } else {
                    this.set('access', resp);
                }
                this.trigger('g:accessFetched');
            }, this)).error(_.bind(function (err) {
                this.trigger('g:error', err);
            }, this));
        } else {
            this.trigger('g:accessFetched');
        }

        return this;
    }
});

girder.models.MetadataMixin = {
    _sendMetadata: function (metadata, successCallback, errorCallback, opts) {
        opts = opts || {};
        girder.restRequest({
            path: opts.path ||
                ((this.altUrl || this.resourceName) + '/' + this.get('_id') + '/metadata'),
            contentType: 'application/json',
            data: JSON.stringify(metadata),
            type: 'PUT',
            error: null
        }).done(_.bind(function (resp) {
            this.set(opts.field || 'meta', resp.meta);
            if (_.isFunction(successCallback)) {
                successCallback();
            }
        }, this)).error(_.bind(function (err) {
            err.message = err.responseJSON.message;
            if (_.isFunction(errorCallback)) {
                errorCallback(err);
            }
        }, this));
    },

    addMetadata: function (key, value, successCallback, errorCallback, opts) {
        opts = opts || {};
        var datum = {};
        datum[key] = value;
        var meta = this.get(opts.field || 'meta');
        if (meta && _.has(meta, key)) {
            if (_.isFunction(errorCallback)) {
                errorCallback({message: key + ' is already a metadata key'});
            }
        } else {
            this._sendMetadata(datum, successCallback, errorCallback, opts);
        }
    },

    removeMetadata: function (key, successCallback, errorCallback, opts) {
        var datum = {};
        datum[key] = null;
        this._sendMetadata(datum, successCallback, errorCallback, opts);
    },

    editMetadata: function (newKey, oldKey, value, successCallback, errorCallback, opts) {
        opts = opts || {};

        if (newKey === oldKey) {
            var datum = {};
            datum[newKey] = value;
            this._sendMetadata(datum, successCallback, errorCallback, opts);
        } else {
            if (_.has(this.get(opts.field || 'meta'), newKey)) {
                if (_.isFunction(errorCallback)) {
                    errorCallback({message: newKey + ' is already a metadata key'});
                }
            } else {
                var metas = {};
                metas[oldKey] = null;
                metas[newKey] = value;
                this._sendMetadata(metas, successCallback, errorCallback, opts);
            }
        }
    }
};
