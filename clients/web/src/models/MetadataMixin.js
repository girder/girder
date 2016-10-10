import _ from 'underscore';

import { restRequest } from 'girder/rest';

var MetadataMixin = {
    _sendMetadata: function (metadata, successCallback, errorCallback, opts) {
        opts = opts || {};
        restRequest({
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

export default MetadataMixin;

