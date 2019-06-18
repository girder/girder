import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit #g-sentry-form': function (event) {
            event.preventDefault();
            this.$('#g-sentry-error-message').empty();

            this._saveSettings([{
                key: 'sentry.dsn',
                value: this.$('#g-sentry-dsn').val().trim()
            }]);
        }
    },
    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['sentry.dsn'])
            }
        }).done((resp) => {
            this.render();
            this.$('#g-sentry-dsn').val(
                resp['sentry.dsn']
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

    _saveSettings: function (settings) {
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
            this.$('#g-sentry-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
