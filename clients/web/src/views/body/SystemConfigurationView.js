/**
 * The system config page for administrators.
 */
girder.views.SystemConfigurationView = girder.View.extend({
    events: {
        'submit .g-settings-form': function (event) {
            event.preventDefault();
            this.$('.g-submit-settings').addClass('disabled');
            this.$('#g-settings-error-message').empty();

            var settings = [];
            for (var i = 0; i < this.settingsKeys.length; i += 1) {
                settings.push({
                    key: this.settingsKeys[i],
                    value: $('#g-' + this.settingsKeys[i].
                             replace(/[_.]/g, '-')).val() || null
                });
            }
            girder.restRequest({
                type: 'PUT',
                path: 'system/setting',
                data: {
                    list: JSON.stringify(settings)
                },
                error: null
            }).done(_.bind(function (resp) {
                this.$('.g-submit-settings').removeClass('disabled');
                girder.events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Settings saved.',
                    type: 'success',
                    timeout: 4000
                });
            }, this)).error(_.bind(function (resp) {
                this.$('.g-submit-settings').removeClass('disabled');
                this.$('#g-settings-error-message').text(resp.responseJSON.message);
            }, this));
        }
    },

    initialize: function () {
        girder.cancelRestRequests('fetch');
        var keys = [
            'core.cookie_lifetime',
            'core.email_from_address',
            'core.registration_policy',
            'core.smtp_host',
            'core.upload_minimum_chunk_size'
        ];
        this.settingsKeys = keys;
        girder.restRequest({
            path: 'system/setting',
            type: 'GET',
            data: {
                list: JSON.stringify(keys),
                default: 'none'
            }
        }).done(_.bind(function (resp) {
            this.settings = resp;
            girder.restRequest({
                path: 'system/setting',
                type: 'GET',
                data: {
                    list: JSON.stringify(keys),
                    default: 'default'
                }
            }).done(_.bind(function (resp) {
                this.defaults = resp;
                this.render();
            }, this));
        }, this));
    },

    render: function () {
        this.$el.html(jade.templates.systemConfiguration({
            settings: this.settings,
            defaults: this.defaults
        }));

        this.$('input[title]').tooltip({
            container: this.$el,
            animation: false,
            delay: {show: 200}
        });

        if (this.settings['core.registration_policy'] !== null) {
            this.$('#g-core-registration-policy').val(
                this.settings['core.registration_policy']
            );
        }

        return this;
    }
});

girder.router.route('settings', 'settings', function () {
    girder.events.trigger('g:navigateTo', girder.views.SystemConfigurationView);
});
