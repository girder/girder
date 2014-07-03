/**
 * Administrative configuration view. Shows the global-level settings for this
 * plugin for all of the supported oauth providers.
 */
girder.views.oauth_ConfigView = girder.View.extend({
    events: {
        'submit #g-oauth-provider-google-form': function (event) {
            event.preventDefault();

            this._saveSettings([{
                key: 'oauth.google_client_id',
                value: this.$('#g-oauth-provider-google-client-id').val().trim()
            }, {
                key: 'oauth.google_client_secret',
                value: this.$('#g-oauth-provider-google-client-secret').val().trim()
            }]);
        }
    },
    initialize: function (settings) {
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.oauth_config());

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
            console.log('do a success alert here', resp);
        }, this)).error(_.bind(function (resp) {
            console.log('do an error alert here', resp);
        }, this));
    }
});

girder.router.route('plugins/oauth/config', 'oauthConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.oauth_ConfigView);
});
