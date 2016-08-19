import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import events from 'girder/events';
import { getCurrentToken, cookie } from 'girder/auth';

var apiRoot = $('#g-global-info-apiroot').text().replace('%HOST%', window.location.origin);
var staticRoot = $('#g-global-info-staticroot').text().replace('%HOST%', window.location.origin);
var uploadHandlers = {};
var uploadChunkSize = 1024 * 1024 * 64; // 64MB

/**
 * Make a request to the REST API. Bind a "done" handler to the return
 * value that will be called when the response is successful. To bind a
 * custom error handler, bind an "error" handler to the return promise,
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
    opts.url = apiRoot + opts.path;

    opts = _.extend(defaults, opts);

    var token = opts.girderToken ||
                getCurrentToken() ||
                cookie.find('girderToken');
    if (token) {
        opts.headers = opts.headers || {};
        opts.headers['Girder-Token'] = token;
    }
    return Backbone.ajax(opts);
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
    apiRoot,
    staticRoot,
    uploadHandlers,
    restRequest,
    numberOutstandingRestRequests,
    cancelRestRequests,
    mockRestRequest,
    unmockRestRequest,
    getUploadChunkSize,
    setUploadChunkSize
};
