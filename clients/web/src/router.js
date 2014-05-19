girder.Router = Backbone.Router.extend({

    execute: function (callback, args) {
        args.push(girder.parseQueryString(args.pop()));
        var queryString = args[args.length - 1];
        if ('dialog' in queryString) {
            queryString.doRouteNavigation = false;
        }
        if (callback) {
            callback.apply(this, args);
        }

        if (queryString.dialog === 'login') {
            girder.events.trigger('g:loginUi');
        }
    }

});

girder.router = new girder.Router();

// When the back button is pressed, we want to close open modals.
girder.router.on('route', function (route, params) {
    if ($('.modal').hasClass('in')) {
        $('.modal').modal('hide');
    }
});
