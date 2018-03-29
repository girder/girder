import View from 'girder/views/View';
import { getCurrentUser } from 'girder/auth';
import { restRequest } from 'girder/rest';
import consentTemplate from './consentTemplate.pug';
import loginTemplate from './loginTemplate.pug';

export default View.extend({
    initialize(opts) {
        // TODO present the name of the client app corresponding to this client ID
        // once we have a consent screen;
        this.redirect = opts.redirect;
        this.state = opts.state;

        restRequest({
            url: `/oauth_client/${opts.clientId}`
        }).then((resp) => {
            this.client = resp;
            if (getCurrentUser()) {
                // Render consent screen
                this.mode = 'consent';
                this.render();
            } else {
                // Render login screen
                this.mode = 'login';
                this.render();
            }
        });
    },

    render() {
        if (this.mode === 'consent') {
            this.$el.html(consentTemplate({
                client: this.client
            }));
        } else if (this.mode === 'login') {
            this.$el.html(loginTemplate({
                client: this.client
            }));
        }
        return this;
    }

});
