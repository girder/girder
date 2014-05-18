
girder.dialogs = {

    splitRoute: function (route) {
        var firstIndex = route.indexOf('?'),
            lastIndex = route.lastIndexOf('?'),
            dialogName,
            baseRoute;

        if (firstIndex === -1) {
            baseRoute = route;
        } else {
            baseRoute = route.slice(0, firstIndex);
        }

        if (lastIndex === -1) {
            dialogName = "";
        } else {
            dialogName = route.slice(lastIndex + 1);
        }

        return {'name': dialogName, 'base': baseRoute};
    },

    handleClose: function (name) {
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute);

        if (routeParts.name === name) {
            girder.router.navigate(routeParts.base);
        }
    },

    handleOpen: function (name) {
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute);
        var viewName = routeParts.base[0].toUpperCase() + routeParts.base.slice(1) + 'View';

        if (viewName in girder.views) {
            girder.events.trigger('g:navigateTo', girder.views[viewName],
                {'doRouteNavigation': false});
        }

        if (routeParts.base === "") {
            girder.router.navigate(curRoute + '?' + name);
        } else if (routeParts.name !== name) {
            girder.router.navigate(routeParts.base + '?' + name);
        }
    }

};
