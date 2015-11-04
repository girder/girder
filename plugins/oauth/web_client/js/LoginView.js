girder.views.oauth_LoginView = girder.View.extend({
    events: {
        'click .g-oauth-button': function (event) {
            var provider = $(event.currentTarget).attr('g-provider');
            window.location = this.providers[provider];
        }
    },

    initialize: function (settings) {
        var redirect = settings.redirect ||
                       girder.dialogs.splitRoute(window.location.href).base;
        this.modeText = settings.modeText || 'log in';

        girder.restRequest({
            path: 'oauth/provider',
            data: {
                redirect: redirect
            }
        }).done(_.bind(function (resp) {
            this.providers = resp;
            this.render();
        }, this));
    },

    render: function () {
        var buttons = [];
        _.each(this.providers, function (url, provider) {
            var btn = this._buttons[provider];

            if (btn) {
                btn.provider = provider;
                buttons.push(btn);
            }
            else {
                console.warn('Unsupported OAuth provider: ' + provider);
            }
        }, this);

        if (buttons.length) {
            this.$el.append(girder.templates.oauth_login({
                modeText: this.modeText,
                buttons: buttons
            }));
        }
    },

    _buttons: {
        google: {
            'icon': 'gplus',
            'text': 'Google',
            'class': 'g-oauth-button-google'
        },
        github: {
            'icon': 'github',
            'text': 'GitHub',
            'class': 'g-oauth-button-github'
        }
    }
});
