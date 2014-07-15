/**
 * Administrative configuration view. Shows the global-level settings for this
 * plugin for all of the supported oauth providers.
 */
girder.views.oauth_ConfigView = girder.View.extend({
    events: {
        'submit #g-oauth-provider-google-form': function (event) {
            event.preventDefault();
            this.$('#g-oauth-provider-google-error-message').empty();

            this._saveSettings([{
                key: 'oauth.google_client_id',
                value: this.$('#g-oauth-provider-google-client-id').val().trim()
            }, {
                key: 'oauth.google_client_secret',
                value: this.$('#g-oauth-provider-google-client-secret').val().trim()
            }]);
        }
    },
    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
              list: JSON.stringify(['oauth.google_client_id',
                                    'oauth.google_client_secret'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#g-oauth-provider-google-client-id').val(
                resp['oauth.google_client_id']
            );
            this.$('#g-oauth-provider-google-client-secret').val(
                resp['oauth.google_client_secret']
            );
        }, this));
    },

    render: function () {
        var origin = window.location.protocol + '//' + window.location.host;
        this.$el.html(jade.templates.oauth_config({
            google: {
                jsOrigin: origin,
                redirectUri: origin + girder.apiRoot + '/oauth/google/callback'
            }
        }));

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'OAuth login',
                el: this.$('.g-config-breadcrumb-container')
            }).render();
        }

        return this;
    },

    _saveSettings: function (settings) {
        girder.restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function (resp) {
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-oauth-provider-google-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

girder.router.route('plugins/oauth/config', 'oauthConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.oauth_ConfigView);
});
