import events from 'girder/events';
import router from 'girder/router';
import { Layout } from 'girder/constants';

import LoginView from './LoginView';


router.route('oauth_provider/login', 'oauthProviderLogin', function (opts) {
    events.trigger('g:navigateTo', LoginView, {
        clientId: opts.clientId,
        redirect: opts.redirect,
        state: opts.state
    }, {
        layout: Layout.EMPTY
    });

});
