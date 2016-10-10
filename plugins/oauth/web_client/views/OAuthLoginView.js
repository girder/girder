import _ from 'underscore';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';
import { splitRoute } from 'girder/misc';

import OAuthLoginViewTemplate from '../templates/oauthLoginView.pug';
import '../stylesheets/oauthLoginView.styl';

var OAuthLoginView = View.extend({
    events: {
        'click .g-oauth-button': function (event) {
            var providerId = $(event.currentTarget).attr('g-provider');
            var provider = _.findWhere(this.providers, {id: providerId});
            window.location = provider.url;
        }
    },

    initialize: function (settings) {
        var redirect = settings.redirect || splitRoute(window.location.href).base;
        this.modeText = settings.modeText || 'log in';
        this.providers = null;

        restRequest({
            path: 'oauth/provider',
            data: {
                redirect: redirect,
                list: true
            }
        }).done(_.bind(function (resp) {
            this.providers = resp;
            this.render();
        }, this));
    },

    render: function () {
        if (this.providers === null) {
            return;
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
                buttons: buttons
            }));
        }
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
        linkedin: {
            icon: 'linkedin',
            class: 'g-oauth-button-linkedin'
        }
    }
});

export default OAuthLoginView;
