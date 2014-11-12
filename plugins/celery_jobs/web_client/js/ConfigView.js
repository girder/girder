/**
 * Administrative configuration view.
 */
girder.views.celery_jobs_ConfigView = girder.View.extend({
    events: {
        'submit #g-celery-jobs-config-form': function (event) {
            event.preventDefault();
            this.$('#g-celery-jobs-error-message').empty();

            this._saveSettings([{
                key: 'celery_jobs.broker_url',
                value: this.$('#celery_jobs_broker').val().trim()
            }, {
                key: 'celery_jobs.app_main',
                value: this.$('#celery_jobs_app_main').val().trim()
            }]);
        }
    },
    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify([
                    'celery_jobs.broker_url',
                    'celery_jobs.app_main'
                ])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#celery_jobs_broker').val(resp['celery_jobs.broker_url']);
            this.$('#celery_jobs_app_main').val(resp['celery_jobs.app_main']);
        }, this));
    },

    render: function () {
        this.$el.html(jade.templates.celery_jobs_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Celery jobs',
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
            this.$('#g-celery-jobs-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

girder.router.route('plugins/celery_jobs/config', 'celeryJobsConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.celery_jobs_ConfigView);
});
