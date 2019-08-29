import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit #g-sentry-server-form': function (event) {
            event.preventDefault();
            this.$('#g-sentry-server-error-message').empty();

            this._saveSettings([{
                key: 'sentry.backend_dsn',
                value: this.$('#g-sentry-server-dsn').val().trim()
            }], {
                errorTarget: '#g-sentry-server-error-message'
            });
        },
        'submit #g-sentry-client-form': function (event) {
            event.preventDefault();
            this.$('#g-sentry-client-error-message').empty();

            this._saveSettings([{
                key: 'sentry.frontend_dsn',
                value: this.$('#g-sentry-client-dsn').val().trim()
            }], {
                errorTarget: '#g-sentry-client-error-message'
            });
        }
    },
    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['sentry.backend_dsn', 'sentry.frontend_dsn'])
            }
        }).done((resp) => {
            this.render();
            this.$('#g-sentry-server-dsn').val(
                resp['sentry.backend_dsn']
            );
            this.$('#g-sentry-client-dsn').val(
                resp['sentry.frontend_dsn']
            );
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Sentry',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _saveSettings: function (settings, params) {
        restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$(params.errorTarget).text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
