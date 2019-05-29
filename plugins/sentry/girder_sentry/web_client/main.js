import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import {init as sentryInit, captureException} from '@sentry/browser';

import './routes';

events.on('g:appload.after', function () {
    restRequest({
        method: 'GET',
        url: 'sentry/dsn'
    }).done((resp) => {
        if (resp.sentry_dsn) {
            // ga('create', resp.sentry_dsn, 'none');
            sentryInit({dsn: resp.sentry_dsn});
            // captureException(new Error("This is my fake error message"));
        }
    });
});
