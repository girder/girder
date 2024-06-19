import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import events from '@girder/core/events';
import { getCurrentToken, setCurrentUser, setCurrentToken } from '@girder/core/auth';

let apiRoot;
var uploadHandlers = {};
var uploadChunkSize = 1024 * 1024 * 64; // 64MB

/**
 * Get the root path to the API.
 *
 * This may be an absolute path, or a path relative to the application root. It will never include
 * a trailing slash.
 *
 * @returns {string}
 */
function getApiRoot() {
    return apiRoot;
}

/**
 * Set the root path to the API.
 *
 * @param {string} root The root path for the API.
 */
function setApiRoot(root) {
    // Strip trailing slash
    apiRoot = root.replace(/\/$/, '');
}

/**
 * Make a request to the REST API.
 *
 * This is a wrapper around {@link http://api.jquery.com/jQuery.ajax/ $.ajax}, which also handles
 * authentication and routing to the Girder API, and provides a default for error notification.
 *
 * Most users of this method should attach a "done" handler to the return value. In cases where the
 * server is ordinarily expected to return a non-200 status (e.g. validating user input), the
 * "error: null" argument should probably be provided, and errors should be processed via an
 * attached "fail" handler.
 *
 * Before this function is called, the API root must be set (which typically happens automatically).
 *
 * @param {Object} opts Options for the request, most of which will be passed through to $.ajax.
 * @param {string} opts.url The resource path, relative to the API root, without leading or trailing
 *        slashes. e.g. "user/login"
 * @param {string} [opts.method='GET'] The HTTP method to invoke.
 * @param {string|Object} [opts.data] The query string or form parameter object.
 * @param {?Function} [opts.error] An error callback, as documented in
 *        {@link http://api.jquery.com/jQuery.ajax/ $.ajax}, or null. If not provided, this will
 *        have a default behavior of triggering a 'g:alert' global event, with details of the
 *        error, and logging the error to the console. It is recommended that you do not ever pass
 *        a non-null callback function, and handle errors via promise rejection handlers instead.
 * @param {string} [opts.girderToken] An alternative auth token to use for this request.
 * @returns {$.Promise} A jqXHR promise, which resolves and rejects
 *          {@link http://api.jquery.com/jQuery.ajax/#jqXHR as documented by $.ajax}.
 */
const restRequest = function (opts) {
    opts = opts || {};
    const defaults = {
        // the default 'method' is 'GET', as set by 'jquery.ajax'

        girderToken: getCurrentToken() || window.localStorage.getItem('girderToken'),

        error: (error, status) => {
            let info;
            if (error.status === 401) {
                setCurrentUser(null);
                setCurrentToken(null);
                events.trigger('g:loginUi');
                info = {
                    text: 'You must log in to view this resource',
                    type: 'warning',
                    timeout: 4000,
                    icon: 'info'
                };
            } else if (error.status === 403) {
                info = {
                    text: 'Access denied. See the console for more details.',
                    type: 'danger',
                    timeout: 5000,
                    icon: 'attention'
                };
            } else if (error.status === 0 && error.statusText === 'abort') {
                /* We expected this abort, so do nothing. */
                return;
            } else if (error.status === 500 && error.responseJSON &&
                error.responseJSON.type === 'girder') {
                info = {
                    text: error.responseJSON.message,
                    type: 'warning',
                    timeout: 5000,
                    icon: 'info'
                };
            } else if (status === 'parsererror') {
                info = {
                    text: 'A parser error occurred while communicating with the ' +
                          'server (did you use the correct value for `dataType`?). ' +
                          'Details have been logged in the console.',
                    type: 'danger',
                    timeout: 5000,
                    icon: 'attention'
                };
            } else {
                info = {
                    text: 'An error occurred while communicating with the ' +
                          'server. Details have been logged in the console.',
                    type: 'danger',
                    timeout: 5000,
                    icon: 'attention'
                };
            }
            events.trigger('g:alert', info);
            console.error(error.status + ' ' + error.statusText, error.responseText);
        }
    };

    // Overwrite defaults with passed opts, but do not mutate opts
    const args = _.extend({}, defaults, opts);

    try {
        // If the data is too large for a GET or PUT request, convert it to a POST request.
        // Girder's REST API handles this for all requests.
        if ((!args.method || args.method === 'GET' || args.method === 'PUT') && args.data && !args.contentType) {
            if (JSON.stringify(args.data).length > 1536) {
                args.headers = args.header || {};
                args.headers['X-HTTP-Method-Override'] = args.method || 'GET';
                args.method = 'POST';
            }
        }
    } catch (err) { }

    if (!args.url) {
        throw new Error('restRequest requires a "url" argument');
    }
    args.url = `${getApiRoot()}${args.url.substring(0, 1) === '/' ? '' : '/'}${args.url}`;

    if (args.girderToken) {
        args.headers = args.headers || {};
        args.headers['Girder-Token'] = args.girderToken;
        delete args.girderToken;
    }

    return Backbone.$.ajax(args);
};

// All requests from Backbone should go through restRequest, adding authentication and the API root.
Backbone.ajax = restRequest;

/* Pending rest requests are listed in this pool so that they can be aborted or
* checked if still processing. */
var restXhrPool = {};
var restXhrCount = 0;
$(document).ajaxSend(function (event, xhr) {
    restXhrCount += 1;
    xhr.girderXhrNumber = restXhrCount;
    restXhrPool[restXhrCount] = xhr;
});
$(document).ajaxComplete(function (event, xhr) {
    var num = xhr.girderXhrNumber;
    if (num && restXhrPool[num]) {
        delete restXhrPool[num];
    }
});

/* Get the number of outstanding rest requests.
 * :param category: if specified, only count those requests that have
 *                  xhr.girder[category] set to a truthy value.
 * :returns: the number of outstanding requests.
 */
function numberOutstandingRestRequests(category) {
    if (category) {
        return _.filter(restXhrPool, function (xhr) {
            return xhr.girder && xhr.girder[category];
        }).length;
    }
    return _.size(restXhrPool);
}

/* Cancel outstanding rest requests.
 * :param category: if specified, only abort those requests that have
 *                  xhr.girder[category] set to a truthy value.
 */
function cancelRestRequests(category) {
    _.each(restXhrPool, function (xhr) {
        if (category && (!xhr.girder || !xhr.girder[category])) {
            return;
        }
        if (xhr.abort) {
            xhr.abort();
        }
    });
}

/*
 * Get Upload Chunk Size
 */
function getUploadChunkSize() {
    return uploadChunkSize;
}

/*
 * Set Upload Chunk Size
 */
function setUploadChunkSize(val) {
    uploadChunkSize = val;
}

export {
    getApiRoot,
    setApiRoot,
    uploadHandlers,
    restRequest,
    numberOutstandingRestRequests,
    cancelRestRequests,
    getUploadChunkSize,
    setUploadChunkSize
};
