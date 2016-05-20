var Backbone      = require('backbone');

var Events        = require('girder/events');
var MiscFunctions = require('girder/utilities/MiscFunctions');

var Router = Backbone.Router.extend({
    initialize: function () {
        this._enabled = true;
    },

    execute: function (callback, args) {
        args.push(MiscFunctions.parseQueryString(args.pop()));
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

var router = new Router();

module.exports = router;
