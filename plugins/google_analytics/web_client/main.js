import _ from 'underscore';

import events from 'girder/events';
import { restRequest } from 'girder/rest';

import './lib/backbone.analytics';
import './routes';

events.on('g:appload.after', function () {
    /*eslint-disable */
    (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
    (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
    m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
    })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
    /*eslint-enable */

    restRequest({
        type: 'GET',
        path: 'google_analytics/id'
    }).done(_.bind(function (resp) {
        if (resp.google_analytics_id) {
            ga('create', resp.google_analytics_id, 'none');
        }
    }, this));
});

/**
 * Add analytics for the hierarchy widget specifically since it routes without
 * triggering (calling navigate without {trigger: true}).
 */
events.on('g:hierarchy.route', function (args) {
    var curRoute = args.route;
    if (!/^\//.test(curRoute)) {
        curRoute = '/' + curRoute;
    }
    /*global ga*/
    ga('send', 'pageview', curRoute);
});
