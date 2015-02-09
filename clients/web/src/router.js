girder.Router = Backbone.Router.extend({
    initialize: function () {
        this._enabled = true;
    },

    execute: function (callback, args) {
        args.push(girder.parseQueryString(args.pop()));
        var queryString = args[args.length - 1];
        if (callback) {
            callback.apply(this, args);
        }

        // handle "top level" dialogs
        if (queryString.dialog === 'login') {
            girder.events.trigger('g:loginUi');
        } else if (queryString.dialog === 'register') {
            girder.events.trigger('g:registerUi');
        } else if (queryString.dialog === 'resetpassword') {
            girder.events.trigger('g:resetPasswordUi');
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

girder.router = new girder.Router();

// When the back button is pressed, we want to close open modals.
girder.router.on('route', function (route, params) {
    if (!params.slice(-1)[0].dialog) {
        $('.modal').girderModal('close');
    }
    // get rid of tooltips
    $('.tooltip').remove();
});
