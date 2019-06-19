import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import './lib/backbone.analytics';
import './routes';

events.on('g:appload.after', function () {
    var dnt = navigator.doNotTrack || window.doNotTrack;
    if (dnt !== '1' && dnt !== 'yes') {
        /* eslint-disable */
        (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
        })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
        /* eslint-enable */

        restRequest({
            method: 'GET',
            url: 'google_analytics/id'
        }).done((resp) => {
            if (resp.google_analytics_id) {
                if (typeof ga !== 'undefined') {
                    ga('create', resp.google_analytics_id, 'none');
                }
            }
        });
    }
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
    if (typeof ga !== 'undefined') {
        /* global ga:false */
        ga('send', 'pageview', curRoute);
    }
});
