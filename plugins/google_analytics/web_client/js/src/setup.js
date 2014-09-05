girder.exposePluginConfig('google_analytics', 'plugins/google_analytics/config');

/**
 * Add analytics for the hierarchy widget specifically since it routes without
 * triggering (calling navigate without {trigger: true}).
 */
girder.events.on('g:hierarchy.route', function (args) {
    var curRoute = args.route;
    if (!/^\//.test(curRoute)) {
        curRoute = '/' + curRoute;
    }
    /*global ga*/
    ga('send', 'pageview', curRoute);
});
