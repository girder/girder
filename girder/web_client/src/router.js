import $ from 'jquery';
import Backbone from 'backbone';

import events from '@girder/core/events';
import { parseQueryString } from '@girder/core/misc';

import '@girder/core/utilities/jquery/girderModal';

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
            events.trigger('g:loginUi');
        } else if (queryString.dialog === 'register') {
            events.trigger('g:registerUi');
        } else if (queryString.dialog === 'resetpassword') {
            events.trigger('g:resetPasswordUi');
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

// When the back button is pressed, we want to close open modals.
router.on('route', function (route, params) {
    if (!params.slice(-1)[0].dialog) {
        $('.modal').girderModal('close');
    }
});

export default router;
