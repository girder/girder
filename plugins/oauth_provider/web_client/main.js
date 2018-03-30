import events from 'girder/events';
import router from 'girder/router';
import { Layout } from 'girder/constants';

import AuthorizeView from './AuthorizeView';


router.route('oauth_provider/authorize', 'oauthProviderAuthorize', function (opts) {
    events.trigger('g:navigateTo', AuthorizeView, {
        clientId: opts.clientId,
        redirect: opts.redirect,
        scope: opts.scope,
        state: opts.state
    }, {
        layout: Layout.EMPTY
    });

});
