import $ from 'jquery';

import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import './routes';

function initGoogleAnalytics(google_analytics_id) {
    $.getScript({
        url: `https://www.googletagmanager.com/gtag/js?id=${google_analytics_id}`,
        success: function () {
            window.dataLayer = window.dataLayer || [];
            function gtag() {
                dataLayer.push(arguments);
            }
            gtag('js', new Date());
            gtag('config', google_analytics_id);
            window.gtag = gtag;
        }
    });
}

events.on('g:appload.after', function () {
    var dnt = navigator.doNotTrack || window.doNotTrack;
    if (dnt !== '1' && dnt !== 'yes') {
        restRequest({
            method: 'GET',
            url: 'google_analytics/id'
        }).done((resp) => {
            if (resp.google_analytics_id) {
                initGoogleAnalytics(resp.google_analytics_id);
            }
        });
    }
});

/**
 * Add analytics for the hierarchy widget specifically since it routes without
 * triggering (calling navigate without {trigger: true}).
 */
events.on('g:hierarchy.route', function (args) {
    let curRoute = args.route;
    if (!/^\//.test(curRoute)) {
        curRoute = '/' + curRoute;
    }
    if (window.gtag) {
        window.gtag('event', 'page_view', { girder_route: curRoute });
    }
});

events.on('g:navigateTo', function (args) {
    let curRoute = location.hash;
    curRoute = curRoute.replace(/^#/, '');
    if (window.gtag) {
        window.gtag('event', 'page_view', { girder_route: curRoute });
    }
});
