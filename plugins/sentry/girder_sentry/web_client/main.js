import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import './lib/backbone.analytics';
import './routes';

events.on('g:appload.after', function () {
    restRequest({
        method: 'GET',
        url: 'sentry/dsn'
    }).done((resp) => {
        if (resp.sentry_dsn) {
            ga('create', resp.sentry_dsn, 'none');
        }
    });
});
