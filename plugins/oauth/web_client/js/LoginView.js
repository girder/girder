girder.views.oauth_LoginView = girder.View.extend({
    events: {
        'click .g-oauth-button': function (event) {
            var provider = $(event.currentTarget).attr('g-provider');
            window.location = this.providers[provider];
        }
    },

    initialize: function () {
        girder.restRequest({
            path: 'oauth/provider',
            data: {
                redirect: 'http://localhost:8080/#collections' // TODO
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
            btn.provider = provider;

            if (btn) {
                buttons.push(btn);
            }
            else {
                console.warn('Unsupported OAuth provider: ' + provider);
            }
        }, this);

        this.$el.append(jade.templates.oauth_login({
            buttons: buttons
        }));
    },

    _buttons: {
        Google: {
            'icon': 'gplus',
            'class': 'g-oauth-button-google'
        }
    }
});
