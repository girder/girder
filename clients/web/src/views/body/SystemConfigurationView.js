/**
 * The system config page for administrators.
 */
girder.views.SystemConfigurationView = girder.View.extend({
    events: {
        'submit .g-settings-form': function (event) {
            event.preventDefault();
            this.$('.g-submit-settings').addClass('disabled');
            this.$('#g-settings-error-message').empty();

            var settings = [{
                key: 'core.cookie_lifetime',
                value: $('#g-cookie-lifetime').val() || null
            }, {
                key: 'core.email_from_address',
                value: $('#g-email-from-address').val() || null
            }, {
                key: 'core.registration_policy',
                value: $('#g-registration-policy').val()
            }, {
                key: 'core.smtp_host',
                value: $('#g-core-smtp-host').val() || null
            }];

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
                this.$('#g-settings-error-message').text(
                    resp.responseJSON.message);
            }, this));
        }
    },

    initialize: function () {
        var keys = [
            'core.cookie_lifetime',
            'core.email_from_address',
            'core.registration_policy',
            'core.smtp_host'
        ];
        girder.restRequest({
            path: 'system/setting',
            type: 'GET',
            data: {
                list: JSON.stringify(keys)
            }
        }).done(_.bind(function (resp) {
            this.settings = resp;
            this.render();
        }, this));
    },

    render: function () {
        this.$el.html(jade.templates.systemConfiguration({
            settings: this.settings
        }));

        this.$('input[title]').tooltip({
            container: this.$el,
            animation: false,
            delay: {show: 200}
        });

        if (this.settings['core.registration_policy'] !== null) {
            this.$('#g-registration-policy').val(
                this.settings['core.registration_policy']);
        }

        return this;
    }
});

girder.router.route('settings', 'settings', function () {
    girder.events.trigger('g:navigateTo', girder.views.SystemConfigurationView);
});
