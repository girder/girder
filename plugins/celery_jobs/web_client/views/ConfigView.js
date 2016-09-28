import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
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
            }, {
                key: 'celery_jobs.celery_user_id',
                value: this.$('#celery_jobs_user_id').val().trim()
            }]);
        }
    },
    initialize: function () {
        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify([
                    'celery_jobs.broker_url',
                    'celery_jobs.app_main',
                    'celery_jobs.celery_user_id'
                ])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#celery_jobs_broker').val(resp['celery_jobs.broker_url']);
            this.$('#celery_jobs_app_main').val(resp['celery_jobs.app_main']);
            this.$('#celery_jobs_user_id').val(resp['celery_jobs.celery_user_id']);
        }, this));
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        this.searchWidget = new SearchFieldWidget({
            el: this.$('.g-celery-user-select-container'),
            placeholder: 'Search for celery user...',
            types: ['user'],
            parentView: this
        }).off().on('g:resultClicked', this._setCeleryUser, this).render();

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Celery jobs',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _setCeleryUser: function (user) {
        this.searchWidget.resetState();
        this.$('#celery_jobs_user_id').val(user.id);
    },

    _saveSettings: function (settings) {
        restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function (resp) {
            events.trigger('g:alert', {
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

export default ConfigView;
