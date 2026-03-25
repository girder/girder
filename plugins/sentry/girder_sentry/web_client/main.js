import { init as sentryInit } from '@sentry/browser';
import './routes';

const events = girder.events;
const { restRequest } = girder.rest;

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
