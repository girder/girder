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
        }
    }

});

if (girder.handleRouting) {
    girder.router = new girder.Router();

    // When the back button is pressed, we want to close open modals.
    girder.router.on('route', function (route, params) {
        /* We have to reach into the backbone modal object a little to see if
         * we need to do anything. */
        if ($('.modal').data('bs.modal') &&
                $('.modal').data('bs.modal').isShown) {
            $('.modal').modal('hide');
        }
        /* This ensures that the modal is fully gone */
        $('.modal').modal('removeBackdrop');
    });

} else {
    girder.router = {
        navigate: function () {},
        route: function () {}
    };
}
