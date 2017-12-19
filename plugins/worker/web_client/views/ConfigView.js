import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import ConfigViewTemplate from '../templates/configView.pug';

var ConfigView = View.extend({
    events: {
        'submit #g-worker-settings-form': function (event) {
            event.preventDefault();
            this.$('#g-worker-settings-error-message').empty();

            this._saveSettings([{
                key: 'worker.api_url',
                value: this.$('#g-worker-api-url').val().trim()
            }, {
                key: 'worker.broker',
                value: this.$('#g-worker-broker').val().trim()
            }, {
                key: 'worker.backend',
                value: this.$('#g-worker-backend').val().trim()
            }, {
                key: 'worker.direct_path',
                value: this.$('#g-worker-direct-path').is(':checked')
            }]);
        }
    },

    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify([
                    'worker.api_url',
                    'worker.broker',
                    'worker.backend',
                    'worker.direct_path'
                ])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#g-worker-api-url').val(resp['worker.api_url']);
            this.$('#g-worker-broker').val(resp['worker.broker']);
            this.$('#g-worker-backend').val(resp['worker.backend']);
            this.$('#g-worker-direct-path').prop('checked', resp['worker.direct_path']);
        }, this));
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Remote worker',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            });
        }

        this.breadcrumb.render();

        return this;
    },

    _saveSettings: function (settings) {
        restRequest({
            method: 'PUT',
            url: 'system/setting',
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
        }, this)).fail(_.bind(function (resp) {
            this.$('#g-worker-settings-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

export default ConfigView;
