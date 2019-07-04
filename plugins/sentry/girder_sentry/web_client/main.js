import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import { init as sentryInit } from '@sentry/browser';

import './routes';

events.on('g:appload.after', function () {
    restRequest({
        method: 'GET',
        url: 'sentry/dsn'
    }).done((resp) => {
        if (resp.sentry_dsn) {
            sentryInit({ dsn: resp.sentry_dsn });
        }
    });
});
