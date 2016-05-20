var $             = require('jquery');
var Backbone      = require('backbone');

var MiscFunctions = require('girder/utilities/MiscFunctions');
var Router        = require('girder/router');

var dialogs = {

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
        if (!Router.enabled()) {
            return;
        }
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute),
            queryString = MiscFunctions.parseQueryString(routeParts.name),
            dialogName = queryString.dialog,
            dialogId = queryString.dialogid;
        delete queryString.dialog;
        delete queryString.dialogid;
        var unparsedQueryString = $.param(queryString);
        if (unparsedQueryString.length > 0) {
            unparsedQueryString = '?' + unparsedQueryString;
        }
        if (dialogName === name && dialogId === nameId) {
            Router.navigate(routeParts.base + unparsedQueryString, options);
        }
    },

    handleOpen: function (name, options, nameId) {
        if (!Router.enabled()) {
            return;
        }
        var curRoute = Backbone.history.fragment,
            routeParts = this.splitRoute(curRoute),
            queryString = MiscFunctions.parseQueryString(routeParts.name),
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
            Router.navigate(routeParts.base + unparsedQueryString, options);
        }
    }

};

module.exports = dialogs;
