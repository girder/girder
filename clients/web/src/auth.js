var MiscFunctions = require('girder/utilities/MiscFunctions');
var Events        = require('girder/events');
var Rest          = require('girder/rest');

// This definitely need some fixing/testing, as it seems that
// girder.corsAuth could be an override. See login doc below.
var corsAuth = false;

var currentUser = null;
var currentToken = MiscFunctions.cookie.find('girderToken');

var getCurrentUser = function () {
    return currentUser;
};

var setCurrentUser = function (user) {
    currentUser = user;
};

var getCurrentToken = function () {
    return currentToken;
};

var setCurrentToken = function (token) {
    currentToken = token;
};

/**
 * Log in to the server. If successful, sets the value of currentUser
 * and currentToken and triggers the "g:login" and "g:login.success".
 * On failure, triggers the "g:login.error" event.
 *
 * @param username The username or email to login as.
 * @param password The password to use.
 * @param cors If the girder server is on a different origin, set this
 *        to "true" to save the auth cookie on the current domain. Alternatively,
 *        you may set the global option "girder.corsAuth = true".
 */
var login = function (username, password, cors) {
    var auth = 'Basic ' + window.btoa(username + ':' + password);
    if (cors === undefined) {
        cors = corsAuth;
    }

    return Rest.restRequest({
        method: 'GET',
        path: '/user/authentication',
        headers: {
            'Girder-Authorization': auth
        },
        error: null
    }).then(function (response) {
        response.user.token = response.authToken;

        var UserModel = require('girder/models/UserModel'); // hmmmm, probably need async
        setCurrentUser(new UserModel(response.user));
        setCurrentToken(response.user.token.token);

        if (cors && !MiscFunctions.cookie.find('girderToken')) {
            // For cross-origin requests, we should write the token into
            // this document's cookie also.
            document.cookie = 'girderToken=' + getCurrentToken();
        }

        Events.trigger('g:login.success', response.user);
        Events.trigger('g:login', response);

        return response.user;
    }, function (jqxhr) {
        Events.trigger('g:login.error', jqxhr.status, jqxhr);
        return jqxhr;
    });
};

var logout = function () {
    return Rest.restRequest({
        method: 'DELETE',
        path: '/user/authentication'
    }).then(function () {
        setCurrentUser(null);
        setCurrentToken(null);

        Events.trigger('g:login', null);
        Events.trigger('g:logout.success');
    }, function (jqxhr) {
        Events.trigger('g:logout.error', jqxhr.status, jqxhr);
    });
};

var fetchCurrentUser = function () {
    return Rest.restRequest({
        method: 'GET',
        path: '/user/me'
    });
};

module.exports = {
    getCurrentUser: getCurrentUser,
    setCurrentUser: setCurrentUser,
    getCurrentToken: getCurrentToken,
    setCurrentToken: setCurrentToken,
    login: login,
    logout: logout,
    fetchCurrentUser: fetchCurrentUser
};
