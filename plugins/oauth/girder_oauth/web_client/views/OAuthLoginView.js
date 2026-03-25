import OAuthLoginViewTemplate from '../templates/oauthLoginView.pug';
import '../stylesheets/oauthLoginView.styl';

const $ = girder.$;
const _ = girder._;
const View = girder.views.View;
const { restRequest } = girder.rest;
const { splitRoute } = girder.misc;

var OAuthLoginView = View.extend({
    events: {
        'click .g-oauth-button': function (event) {
            var providerId = $(event.currentTarget).attr('g-provider');
            var provider = _.findWhere(this.providers, { id: providerId });
            window.location = provider.url;
        }
    },

    initialize: function (settings) {
        var redirect = settings.redirect || splitRoute(window.location.href).base;
        this.modeText = settings.modeText || 'log in';
        this.providers = null;
        this.enablePasswordLogin = _.has(settings, 'enablePasswordLogin') ? settings.enablePasswordLogin : true;

        restRequest({
            url: 'oauth/provider',
            data: {
                redirect: redirect,
                list: true
            }
        }).done((resp) => {
            this.providers = resp;
            this.render();
        });
    },

    render: function () {
        if (this.providers === null) {
            return this;
        }

        var buttons = [];
        _.each(this.providers, function (provider) {
            var btn = this._buttons[provider.id];

            if (btn) {
                btn.providerId = provider.id;
                btn.text = provider.name;
                buttons.push(btn);
            } else {
                console.warn('Unsupported OAuth2 provider: ' + provider.id);
            }
        }, this);

        if (buttons.length) {
            this.$el.append(OAuthLoginViewTemplate({
                modeText: this.modeText,
                buttons: buttons,
                enablePasswordLogin: this.enablePasswordLogin
            }));
        }

        return this;
    },

    _buttons: {
        google: {
            icon: 'gplus',
            class: 'g-oauth-button-google'
        },
        globus: {
            icon: 'globe',
            class: 'g-oauth-button-globus'
        },
        github: {
            icon: 'github-circled',
            class: 'g-oauth-button-github'
        },
        bitbucket: {
            icon: 'bitbucket',
            class: 'g-oauth-button-bitbucket'
        },
        microsoft: {
            icon: 'microsoft',
            class: 'g-oauth-button-microsoft'
        },
        linkedin: {
            icon: 'linkedin',
            class: 'g-oauth-button-linkedin'
        },
        box: {
            icon: 'box',
            class: 'g-oauth-button-box'
        },
        cilogon: {
            icon: 'cilogon',
            class: 'g-oauth-button-box'
        }
    }
});

export default OAuthLoginView;
