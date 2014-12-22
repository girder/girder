/**
 * Administrative configuration view. Shows the global-level settings for this
 * plugin for setting the Google Analytics tracking ID.
 */
girder.views.google_analytics_ConfigView = girder.View.extend({
    events: {
        'submit #g-google_analytics-form': function (event) {
            event.preventDefault();
            this.$('#g-google_analytics-error-message').empty();

            this._saveSettings([{
                key: 'google_analytics.tracking_id',
                value: this.$('#google_analytics.tracking_id').val().trim()
            }]);
        }
    },
    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['google_analytics.tracking_id'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#google_analytics.tracking_id').val(
                resp['google_analytics.tracking_id']
            );
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.google_analytics_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Google Analytics',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
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
            this.$('#g-google_analytics-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

girder.router.route('plugins/google_analytics/config', 'google_analyticsConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.google_analytics_ConfigView);
});
