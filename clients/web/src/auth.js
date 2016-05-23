import _         from 'underscore';

import Events    from 'girder/events';
import UserModel from 'girder/models/UserModel';

// This definitely need some fixing/testing, as it seems that
// girder.corsAuth could be an override. See login doc below.
var corsAuth = false;

export var cookie = {
    findAll: function () {
        var cookies = {};
        _(document.cookie.split(';'))
            .chain()
            .map(function (m) {
                return m.replace(/^\s+/, '').replace(/\s+$/, '');
            })
            .each(function (c) {
                var arr = c.split('='),
                    key = arr[0],
                    value = null,
                    size = _.size(arr);
                if (size > 1) {
                    value = arr.slice(1).join('');
                }
                cookies[key] = value;
            });
        return cookies;
    },

    find: function (name) {
        var cookie = null,
            list = this.findAll();

        _.each(list, function (value, key) {
            if (key === name) {
                cookie = value;
            }
        });
        return cookie;
    }
};

var currentUser = null;
var currentToken = cookie.find('girderToken');

export var getCurrentUser = function () {
    return currentUser;
};

export var setCurrentUser = function (user) {
    currentUser = user;
};

export var getCurrentToken = function () {
    return currentToken;
};

export var setCurrentToken = function (token) {
    currentToken = token;
};

export var fetchCurrentUser = function () {
    return Rest.restRequest({
        method: 'GET',
        path: '/user/me'
    });
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
export var login = function (username, password, cors) {
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

        setCurrentUser(new UserModel(response.user));
        setCurrentToken(response.user.token.token);

        if (cors && !cookie.find('girderToken')) {
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

export var logout = function () {
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

// Alleviate a circular dependency for now
// http://stackoverflow.com/a/30390378/250457
import Rest   from 'girder/rest';
