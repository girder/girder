/**
 * The system config page for administrators.
 */
girder.views.SystemConfigurationView = girder.View.extend({
    events: {
        'submit .g-settings-form': function (event) {
            event.preventDefault();
            this.$('.g-submit-settings').addClass('disabled');
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

        return this;
    }
});

girder.router.route('settings', 'settings', function () {
    girder.events.trigger('g:navigateTo', girder.views.SystemConfigurationView);
});
