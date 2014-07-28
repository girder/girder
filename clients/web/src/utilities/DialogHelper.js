
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
        if (!girder.handleRouting) {
            return;
        }
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute),
            queryString = girder.parseQueryString(routeParts.name),
            dialogName = queryString.dialog;
        delete queryString.dialog;
        var unparsedQueryString = $.param(queryString);
        if (unparsedQueryString.length > 0) {
            unparsedQueryString = '?' + unparsedQueryString;
        }
        if (dialogName === name) {
            girder.router.navigate(routeParts.base + unparsedQueryString);
        }
    },

    handleOpen: function (name) {
        if (!girder.handleRouting) {
            return;
        }
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute),
            queryString = girder.parseQueryString(routeParts.name),
            dialogName = queryString.dialog;

        if (dialogName !== name) {
            queryString.dialog = name;
            var unparsedQueryString = $.param(queryString);
            if (unparsedQueryString.length > 0) {
                unparsedQueryString = '?' + unparsedQueryString;
            }
            girder.router.navigate(routeParts.base + unparsedQueryString);
        }
    }

};
