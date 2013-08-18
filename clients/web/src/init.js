// This script must be invoked first to declare the girder namespace
var girder = {
    routes: {},
    models: {},
    collections: {},
    views: {},
    apiRoot: '/api/v1',
    currentUser: null,
    pages: {},
    events: _.extend({}, Backbone.Events),

    /**
     * Make a request to the REST API. Bind a "done" handler to the return
     * value that will be called when the response is successful. To bind a
     * custom error handler, bind an "error" handler to the return promise,
     * which will be executed in addition to the normal behavior of logging
     * the error to the console. To override the default error handling
     * behavior, pass an "error" key in your opts object; this should be done
     * any time the server might throw an exception from validating user input,
     * e.g. logging in, registering, or generally filling out forms.
     * @param path The resource path, e.g. "user/login"
     * @param data The form parameter object.
     * @param [type='GET'] The HTTP method to invoke.
     */
    restRequest: function (opts) {
        var defaults = {
            dataType: 'json',
            type: 'GET',

            error: function (error) {
                alert('An error occurred while communicating with the server. ' +
                      'Details have been logged in the console.');
                console.error(error.status + ' ' + error.statusText, error.responseText);
                girder.lastError = error;
            }
        };

        if (opts.path.substring(0, 1) != '/') {
            opts.path = '/' + opts.path;
        }
        opts.url = girder.apiRoot + opts.path;

        return Backbone.ajax(_.extend(defaults, opts));
    }
};

// When all scripts are loaded, we invoke the application
$(function () {
    new girder.App({});
});
