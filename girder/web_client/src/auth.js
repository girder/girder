import _ from 'underscore';

import UserModel from '@girder/core/models/UserModel';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

// TODO: this might need some fixing/testing, as it seems that
// girder.corsAuth could be an override. See login doc below.
var corsAuth = false;

var cookie = {
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
        var foundCookie = null,
            list = this.findAll();

        _.each(list, function (value, key) {
            if (key === name) {
                foundCookie = value;
            }
        });
        return foundCookie;
    }
};

var currentUser = null;
var currentToken = cookie.find('girderToken');

function getCurrentUser() {
    return currentUser;
}

function setCurrentUser(user) {
    currentUser = user;
}

function getCurrentToken() {
    return currentToken;
}

function setCurrentToken(token) {
    currentToken = token;
}

function fetchCurrentUser() {
    return restRequest({
        method: 'GET',
        url: '/user/me'
    });
}

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
 * @param otpToken An optional one-time password to include with the login.
 */
function login(username, password, cors = corsAuth, otpToken = null) {
    var auth = 'Basic ' + window.btoa(username + ':' + password);

    const headers = {
        'Girder-Authorization': auth
    };
    if (_.isString(otpToken)) {
        // Use _.isString to send header with empty string
        headers['Girder-OTP'] = otpToken;
    }
    return restRequest({
        method: 'GET',
        url: '/user/authentication',
        headers: headers,
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

        events.trigger('g:login.success', response.user);
        events.trigger('g:login', response);

        return response.user;
    }).fail(function (jqxhr) {
        events.trigger('g:login.error', jqxhr.status, jqxhr);
    });
}

function logout() {
    return restRequest({
        method: 'DELETE',
        url: '/user/authentication'
    }).done(function () {
        setCurrentUser(null);
        setCurrentToken(null);

        events.trigger('g:login', null);
        events.trigger('g:logout.success');
    }).fail(function (jqxhr) {
        events.trigger('g:logout.error', jqxhr.status, jqxhr);
    });
}

export {
    cookie,
    corsAuth,
    getCurrentUser,
    setCurrentUser,
    getCurrentToken,
    setCurrentToken,
    fetchCurrentUser,
    login,
    logout
};
