/*global girder:true*/
/*global console:true*/

'use strict';

/*
 * Initialize global girder object
 */
var girder = girder || {};

/*
 * Some cross-browser globals
 */
if (!window.console) {
    var console = {
        log: $.noop,
        error: $.noop
    };
}

_.extend(girder, {
    models: {},
    collections: {},
    views: {},
    apiRoot: $('#g-global-info-apiroot').text().replace(
        '%HOST%', window.location.origin),
    staticRoot: $('#g-global-info-staticroot').text().replace(
        '%HOST%', window.location.origin),
    currentUser: null,
    currentToken: null,
    events: _.clone(Backbone.Events),
    uploadHandlers: {},
    corsAuth: girder.corsAuth || false,

    /**
     * Constants and enums:
     */
    UPLOAD_CHUNK_SIZE: 1024 * 1024 * 64, // 64MB
    SORT_ASC: 1,
    SORT_DESC: -1,
    MONTHS: [
        'January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December'
    ],
    AccessType: {
        NONE: -1,
        READ: 0,
        WRITE: 1,
        ADMIN: 2
    },
    AssetstoreType: {
        FILESYSTEM: 0,
        GRIDFS: 1,
        S3: 2
    },
    Layout: {
        DEFAULT: 'default',
        EMPTY: 'empty'
    },
    layout: 'default',

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
    restRequest: function (opts) {
        opts = opts || {};
        var defaults = {
            dataType: 'json',
            type: 'GET',

            error: function (error, status) {
                var info;
                if (error.status === 401) {
                    girder.events.trigger('g:loginUi');
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
                girder.events.trigger('g:alert', info);
                console.error(error.status + ' ' + error.statusText, error.responseText);
                girder.lastError = error;
            }
        };

        if (opts.path.substring(0, 1) !== '/') {
            opts.path = '/' + opts.path;
        }
        opts.url = girder.apiRoot + opts.path;

        opts = _.extend(defaults, opts);

        var token = opts.girderToken ||
                    girder.currentToken ||
                    girder.cookie.find('girderToken');
        if (token) {
            opts.headers = opts.headers || {};
            opts.headers['Girder-Token'] = token;
        }
        return Backbone.ajax(opts);
    },

    /**
     * Log in to the server. If successful, sets the value of girder.currentUser
     * and girder.currentToken and triggers the "g:login" and "g:login.success".
     * On failure, triggers the "g:login.error" event.
     *
     * @param username The username or email to login as.
     * @param password The password to use.
     * @param cors If the girder server is on a different origin, set this
     *        to "true" to save the auth cookie on the current domain. Alternatively,
     *        you may set the global option "girder.corsAuth = true".
     */
    login: function (username, password, cors) {
        var auth = 'Basic ' + window.btoa(username + ':' + password);
        if (cors === undefined) {
            cors = girder.corsAuth;
        }

        return girder.restRequest({
            method: 'GET',
            path: '/user/authentication',
            headers: {
                'Girder-Authorization': auth
            },
            error: null
        }).then(function (response) {
            response.user.token = response.authToken;

            girder.currentUser = new girder.models.UserModel(response.user);
            girder.currentToken = response.user.token.token;

            if (cors && !girder.cookie.find('girderToken')) {
                // For cross-origin requests, we should write the token into
                // this document's cookie also.
                document.cookie = 'girderToken=' + girder.currentToken;
            }

            girder.events.trigger('g:login.success', response.user);
            girder.events.trigger('g:login', response);

            return response.user;
        }, function (jqxhr) {
            girder.events.trigger('g:login.error', jqxhr.status, jqxhr);
            return jqxhr;
        });
    },

    logout: function () {
        return girder.restRequest({
            method: 'DELETE',
            path: '/user/authentication'
        }).then(function () {
            girder.currentUser = null;
            girder.currentToken = null;

            girder.events.trigger('g:login', null);
            girder.events.trigger('g:logout.success');
        }, function (jqxhr) {
            girder.events.trigger('g:logout.error', jqxhr.status, jqxhr);
        });
    },

    fetchCurrentUser: function () {
        return girder.restRequest({
            method: 'GET',
            path: '/user/me'
        });
    }
});

/**
 * The old "jade.templates" namespace is deprecated as of version 1.1, but is
 * retained here for backward compatibility. It will be removed in version 2.0.
 */
/* jshint -W079 */
var jade = jade || {};
jade.templates = girder.templates;
