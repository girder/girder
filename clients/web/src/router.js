girder.Router = Backbone.Router.extend({

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
    }

});

if (girder.handleRouting) {
    girder.router = new girder.Router();

    // When the back button is pressed, we want to close open modals.
    girder.router.on('route', function (route, params) {
        if (!params.slice(-1)[0].dialog) {
            $('.modal').girderModal('close');
        }
        // get rid of tooltips
        $('.tooltip').remove();
    });

} else {
    girder.router = {
        navigate: function () {},
        route: function () {}
    };
}
