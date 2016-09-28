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
                key: 'worker.broker',
                value: this.$('#g-worker-broker').val().trim()
            }, {
                key: 'worker.backend',
                value: this.$('#g-worker-backend').val().trim()
            }]);
        }
    },

    initialize: function () {
        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify([
                    'worker.broker',
                    'worker.backend'
                ])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#g-worker-broker').val(resp['worker.broker']);
            this.$('#g-worker-backend').val(resp['worker.backend']);
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
            this.$('#g-worker-settings-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

export default ConfigView;
