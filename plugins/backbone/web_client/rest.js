import _ from 'underscore';
import Backbone from 'backbone';

import { getCurrentToken } from 'girder/auth';
import { apiRoot } from 'girder/rest';

/**
 * Wrap the Backbone.ajax method to automatically inject an
 * authentication token for requests going to girder's api.
 */
Backbone.ajax = _.wrap(Backbone.ajax, function (ajax, ...args) {
    const opts = args[0];

    if (_.isObject(opts) && (opts.url || '').startsWith(apiRoot)) {
        opts.headers = opts.headers || {};
        _.defaults(opts.headers, {
            'Girder-Token': getCurrentToken()
        });
    }
    return ajax.apply(this, args);
});
