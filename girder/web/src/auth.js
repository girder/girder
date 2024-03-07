import _ from 'underscore';

import UserModel from '@girder/core/models/UserModel';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

// TODO: this might need some fixing/testing, as it seems that
// girder.corsAuth could be an override. See login doc below.
var corsAuth = false;
var currentUser = null;
var currentToken = window.localStorage.getItem('girderToken');

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
 * Encode password using TextEncoder to support unicode
 */
function basicAuthEncode(username, password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(username + ':' + password);
    return 'Basic ' + btoa(String.fromCharCode(...data));
}

/**
 * Log in to the server. If successful, sets the value of currentUser
 * and currentToken and triggers the "g:login" and "g:login.success".
 * On failure, triggers the "g:login.error" event.
 *
 * @param username The username or email to login as.
 * @param password The password to use.
 * @param otpToken An optional one-time password to include with the login.
 */
function login(username, password, otpToken = null) {
    var auth = basicAuthEncode(username, password);

    const headers = {
        Authorization: auth
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

        window.localStorage.setItem('girderToken', response.user.token.token);

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

        window.localStorage.removeItem('girderToken');

        events.trigger('g:login', null);
        events.trigger('g:logout.success');
    }).fail(function (jqxhr) {
        events.trigger('g:logout.error', jqxhr.status, jqxhr);
    });
}

export {
    corsAuth,
    getCurrentUser,
    setCurrentUser,
    getCurrentToken,
    setCurrentToken,
    fetchCurrentUser,
    login,
    logout
};
