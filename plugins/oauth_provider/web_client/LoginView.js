import $ from 'jquery';
import View from 'girder/views/View';
import { getCurrentUser } from 'girder/auth';
import { restRequest } from 'girder/rest';
import consentTemplate from './consentTemplate.pug';
import loginTemplate from './loginTemplate.pug';

export default View.extend({
    events: {

    },
    initialize(opts) {
        // TODO present the name of the client app corresponding to this client ID
        // once we have a consent screen;
        this.redirect = opts.redirect;
        this.state = opts.state;

        const clientFetchXhr = restRequest({
            url: `/oauth_client/${opts.clientId}`
        }).done((resp) => resp);

        const scopeFetchXhr = restRequest({
            url: 'token/scopes'
        }).done((resp) => resp);

        $.when(clientFetchXhr, scopeFetchXhr).then((client, scopeInfo) => {
            this.client = client;
            this.scopeInfo = scopeInfo;
            this.mode = getCurrentUser() ? 'consent' : 'login';
            this.render();
        });
    },

    render() {
        if (this.mode === 'consent') {
            this.$el.html(consentTemplate({
                client: this.client
            }));
        } else if (this.mode === 'login') {
            this.$el.html(loginTemplate());
        }
        return this;
    }
});
