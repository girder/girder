import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import events from 'girder/events';
import { getCurrentToken, cookie } from 'girder/auth';

let apiRoot;
let staticRoot;
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
 * Get the root path to the static content.
 *
 * This may be an absolute path, or a path relative to the application root. It will never include
 * a trailing slash.
 *
 * @returns {string}
 */
function getStaticRoot() {
    return staticRoot;
}

/**
 * Set the root path to the static content.
 *
 * @param {string} root The root path for the static content.
 */
function setStaticRoot(root) {
    // Strip trailing slash
    staticRoot = root.replace(/\/$/, '');
    // publicPath would normally be set in the Webpack config file, but is not known at compile
    // time.
    __webpack_public_path__ = `${getStaticRoot()}/built/`; // eslint-disable-line no-undef, camelcase
    // Note that in theory, an ES6-style import of a file asset that occurred earlier in the import
    // resolution sequence than this module could fail to have its publicPath set at all, but the
    // typical style rules for ordering ES6-style imports ensure that this module will be loaded
    // very early in the import sequence. However, if App startup code modifies the staticRoot, then
    // any ES6-style imports will probably have the incorrect path. Ultimately though, most file
    // asset imports will occur in Pug files via require-style imports, which happen at runtime, so
    // they will always succeed.
}

// Initialize the API and static roots (at JS load time)
// This could be overridden when the App is started, but we need sensible defaults so models, etc.
// can be easily used without having to start an App or explicitly set these values
setApiRoot(
    $('#g-global-info-apiroot').text().replace('%HOST%', window.location.origin) || '/api/v1'
);
setStaticRoot(
    $('#g-global-info-staticroot').text().replace('%HOST%', window.location.origin) || '/static'
);

/**
 * Make a request to the REST API. Bind a "done" handler to the return
 * value that will be called when the response is successful. To bind a
 * custom error handler, bind a "fail" handler to the return promise,
 * which will be executed in addition to the normal behavior of logging
 * the error to the console. To override the default error handling
 * behavior, pass an "error" key in your opts object; this should be done
 * any time the server might throw an exception from validating user input,
 * e.g. logging in, registering, or generally filling out forms.
 *
 * @param path The resource path, e.g. "user/login"
 * @param data The form parameter object.
 * @param [type='GET'] The HTTP method to invoke.
 * @param [girderToken] An alternative auth token to use for this request.
 */
function __restRequest(opts) {
    opts = opts || {};
    var defaults = {
        dataType: 'json',
        type: 'GET',

        error: function (error, status) {
            var info;
            if (error.status === 401) {
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

    if (opts.path.substring(0, 1) !== '/') {
        opts.path = '/' + opts.path;
    }
    opts.url = getApiRoot() + opts.path;

    opts = _.extend(defaults, opts);

    var token = opts.girderToken ||
                getCurrentToken() ||
                cookie.find('girderToken');
    if (token) {
        opts.headers = opts.headers || {};
        opts.headers['Girder-Token'] = token;
    }

    let jqXHR = Backbone.ajax(opts);
    jqXHR.error = function () {
        console.warn('Use of restRequest.error is deprecated, use restRequest.fail instead.');
        return jqXHR.fail.apply(jqXHR, arguments);
    };
    return jqXHR;
}

/**
 * Make a request to the REST API.
 *
 * Provide an API to mock this single conduit connecting the client to the server.
 * While this can be done with various testing framework, choosing the right one depends on the
 * way our code is bundled (spyOn() vs. rewire(), for example). Let's provide a specific API
 * to mock restRequest nonetheless, since it is likely to be mocked the most.
 */
var restRequestMock = null;
function restRequest() {
    if (restRequestMock) {
        return restRequestMock.apply(this, arguments);
    }
    return __restRequest.apply(this, arguments);
}
function mockRestRequest(mock) {
    restRequestMock = mock;
}
function unmockRestRequest(mock) {
    restRequestMock = null;
}

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
    apiRoot, // deprecated
    staticRoot, // deprecated
    getApiRoot,
    setApiRoot,
    getStaticRoot,
    setStaticRoot,
    uploadHandlers,
    restRequest,
    numberOutstandingRestRequests,
    cancelRestRequests,
    mockRestRequest,
    unmockRestRequest,
    getUploadChunkSize,
    setUploadChunkSize
};
