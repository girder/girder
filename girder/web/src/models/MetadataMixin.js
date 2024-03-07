import _ from 'underscore';

import { restRequest } from '@girder/core/rest';

var MetadataMixin = {
    _sendMetadata: function (metadata, successCallback, errorCallback, opts) {
        opts = opts || {};
        restRequest({
            url: opts.path ||
                ((this.altUrl || this.resourceName) + `/${this.id}/metadata?allowNull=true`),
            contentType: 'application/json',
            data: JSON.stringify(metadata),
            method: 'PUT',
            error: null
        }).done((resp) => {
            this.set(opts.field || 'meta', resp.meta);
            if (_.isFunction(successCallback)) {
                successCallback();
            }
        }).fail((err) => {
            err.message = err.responseJSON.message;
            if (_.isFunction(errorCallback)) {
                errorCallback(err);
            }
        });
    },

    addMetadata: function (key, value, successCallback, errorCallback, opts) {
        opts = opts || {};
        var datum = {};
        datum[key] = value;
        var meta = this.get(opts.field || 'meta');
        if (meta && _.has(meta, key)) {
            if (_.isFunction(errorCallback)) {
                errorCallback({ message: key + ' is already a metadata key' });
            }
        } else {
            this._sendMetadata(datum, successCallback, errorCallback, opts);
        }
    },

    removeMetadata: function (key, successCallback, errorCallback, opts) {
        if (!_.isArray(key)) {
            key = [key];
        }
        restRequest({
            url: opts.path ||
                ((this.altUrl || this.resourceName) + `/${this.id}/metadata`),
            contentType: 'application/json',
            data: JSON.stringify(key),
            method: 'DELETE',
            error: null
        }).done((resp) => {
            this.set(opts.field || 'meta', resp.meta);
            if (_.isFunction(successCallback)) {
                successCallback();
            }
        }).fail((err) => {
            err.message = err.responseJSON.message;
            if (_.isFunction(errorCallback)) {
                errorCallback(err);
            }
        });
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
                    errorCallback({ message: newKey + ' is already a metadata key' });
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
