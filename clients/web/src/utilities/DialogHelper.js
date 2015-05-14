
girder.dialogs = {

    splitRoute: function (route) {
        if (!route) {
            return {base: '', name: ''};
        }
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
            dialogName = '';
        } else {
            dialogName = route.slice(lastIndex + 1);
        }

        return {name: dialogName, base: baseRoute};
    },

    handleClose: function (name, options, nameId) {
        if (!girder.router.enabled()) {
            return;
        }
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute),
            queryString = girder.parseQueryString(routeParts.name),
            dialogName = queryString.dialog,
            dialogId = queryString.dialogid;
        delete queryString.dialog;
        delete queryString.dialogid;
        var unparsedQueryString = $.param(queryString);
        if (unparsedQueryString.length > 0) {
            unparsedQueryString = '?' + unparsedQueryString;
        }
        if (dialogName === name && dialogId === nameId) {
            girder.router.navigate(routeParts.base + unparsedQueryString, options);
        }
    },

    handleOpen: function (name, options, nameId) {
        if (!girder.router.enabled()) {
            return;
        }
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute),
            queryString = girder.parseQueryString(routeParts.name),
            dialogName = queryString.dialog,
            dialogId = queryString.dialogid;

        if (dialogName !== name || nameId !== dialogId) {
            queryString.dialog = name;
            if (nameId) {
                queryString.dialogid = nameId;
            }
            var unparsedQueryString = $.param(queryString);
            if (unparsedQueryString.length > 0) {
                unparsedQueryString = '?' + unparsedQueryString;
            }
            girder.router.navigate(routeParts.base + unparsedQueryString, options);
        }
    }

};
