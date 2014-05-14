girder.Router = Backbone.Router.extend({
});

girder.router = new girder.Router();

girder.router.on('route', function (route, params) {
    if (route !== 'login' && route !== 'register' && route !== 'upload') {
        $('.modal').modal('hide');
    }
});
