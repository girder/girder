import $ from 'jquery';

import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import './routes';

function initGoogleAnalytics(googleAnalyticsId) {
    $.getScript({
        url: `https://www.googletagmanager.com/gtag/js?id=${googleAnalyticsId}`,
        success: function () {
            window.dataLayer = window.dataLayer || [];
            function gtag() {
                dataLayer.push(arguments); // eslint-disable-line no-undef
            }
            gtag('js', new Date());
            gtag('config', googleAnalyticsId);
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
            if (resp.googleAnalyticsId) {
                initGoogleAnalytics(resp.googleAnalyticsId);
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
