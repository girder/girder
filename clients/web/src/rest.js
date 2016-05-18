var $             = require('jquery');
var _             = require('underscore');
var Backbone      = require('backbone');
var Auth          = require('girder/auth');
var Events        = require('girder/events');

var apiRoot = $('#g-global-info-apiroot').text().replace('%HOST%', window.location.origin);
var staticRoot = $('#g-global-info-staticroot').text().replace('%HOST%', window.location.origin);
var uploadHandlers = {};

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
var restRequest = function (opts) {
    opts = opts || {};
    var defaults = {
        dataType: 'json',
        type: 'GET',

        error: function (error, status) {
            var info;
            if (error.status === 401) {
                Events.trigger('g:loginUi');
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
            Events.trigger('g:alert', info);
            console.error(error.status + ' ' + error.statusText, error.responseText);
        }
    };

    if (opts.path.substring(0, 1) !== '/') {
        opts.path = '/' + opts.path;
    }
    opts.url = apiRoot + opts.path;

    opts = _.extend(defaults, opts);

    var token = opts.girderToken ||
                Auth.getCurrentToken() ||
                Auth.cookie.find('girderToken');
    if (token) {
        opts.headers = opts.headers || {};
        opts.headers['Girder-Token'] = token;
    }
    return Backbone.ajax(opts);
};

module.exports = {
    apiRoot: apiRoot,
    staticRoot: staticRoot,
    uploadHandlers: uploadHandlers,
    restRequest: restRequest
};
