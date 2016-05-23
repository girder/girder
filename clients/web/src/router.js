import Backbone             from 'backbone';

import Events               from 'girder/events';
import { parseQueryString } from 'girder/utilities/MiscFunctions';

var Router = Backbone.Router.extend({
    initialize: function () {
        this._enabled = true;
    },

    execute: function (callback, args) {
        args.push(parseQueryString(args.pop()));
        var queryString = args[args.length - 1];
        if (callback) {
            callback.apply(this, args);
        }

        // handle "top level" dialogs
        if (queryString.dialog === 'login') {
            Events.trigger('g:loginUi');
        } else if (queryString.dialog === 'register') {
            Events.trigger('g:registerUi');
        } else if (queryString.dialog === 'resetpassword') {
            Events.trigger('g:resetPasswordUi');
        }
    },

    /**
     * Set or get the enabled state of the router. Call with a boolean argument
     * to set the enabled state, or with no arguments to get the state.
     */
    enabled: function () {
        if (arguments.length) {
            this._enabled = !!arguments[0];
        }
        return this._enabled;
    },

    navigate: function () {
        if (this._enabled) {
            Backbone.Router.prototype.navigate.apply(this, arguments);
        }
    }
});

export var router = new Router();
