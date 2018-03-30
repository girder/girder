import $ from 'jquery';
import _ from 'underscore';
import View from 'girder/views/View';
import { getCurrentUser } from 'girder/auth';
import { restRequest } from 'girder/rest';
import consentTemplate from './consentTemplate.pug';
import loginTemplate from './loginTemplate.pug';
import './authorizeView.styl';

const getScopeInfo = (id) => _.find

export default View.extend({
    events: {

    },
    initialize(opts) {
        // TODO present the name of the client app corresponding to this client ID
        // once we have a consent screen;
        this.redirect = opts.redirect;
        this.state = opts.state;
        this.scopes = opts.scope.split(' ');

        const clientFetchXhr = restRequest({
            url: `/oauth_client/${opts.clientId}`
        }).then((resp) => resp);

        const scopeFetchXhr = restRequest({
            url: 'token/scopes'
        }).then((resp) => resp);

        $.when(clientFetchXhr, scopeFetchXhr).done((client, scopeInfo) => {
            this.client = client;
            this.scopeInfo = scopeInfo.custom.concat(scopeInfo.adminCustom || []);
            this.mode = getCurrentUser() ? 'consent' : 'login';
            this.render();
        });
    },

    render() {
        if (this.mode === 'consent') {
            this.$el.html(consentTemplate({
                client: this.client,
                getScopeInfo: this.getScopeInfo.bind(this),
                scopes: this.scopes,
                user: getCurrentUser(),
            }));
        } else if (this.mode === 'login') {
            this.$el.html(loginTemplate());
        }
        return this;
    },

    getScopeInfo(scopeId) {
        return _.find(this.scopeInfo, (info) => info.id === scopeId);
    }
});
