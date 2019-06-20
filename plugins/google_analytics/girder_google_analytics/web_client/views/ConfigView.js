import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit #g-google_analytics-form': function (event) {
            event.preventDefault();
            this.$('#g-google_analytics-error-message').empty();

            this._saveSettings([{
                key: 'google_analytics.tracking_id',
                value: this.$('#g-google-analytics-tracking-id').val().trim()
            }]);
        }
    },
    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['google_analytics.tracking_id'])
            }
        }).done((resp) => {
            this.render();
            this.$('#g-google-analytics-tracking-id').val(
                resp['google_analytics.tracking_id']
            );
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Google Analytics',
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
            this.$('#g-google_analytics-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
