girder.Router = Backbone.Router.extend({
});

girder.router = new girder.Router();

// When the back button is pressed, we want to close open modals.
girder.router.on('route', function (route, params) {
    if ($('.modal').hasClass('in')) {
        $('.modal').modal('hide');
    }
});
