import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import template from '../templates/config.pug';

var ConfigView = View.extend({
    events: {
        'submit #g-hashsum-download-config-form': function (event) {
            event.preventDefault();
            this.$('#g-hashsum-download-error-message').empty();

            this._saveSettings([{
                key: 'hashsum_download.auto_compute',
                value: this.$('#g-hashsum-download-auto-compute').is(':checked')
            }]);
        }
    },

    initialize: function () {
        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'Hashsum download',
            parentView: this
        });

        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify([
                    'hashsum_download.auto_compute'
                ])
            }
        }).done((resp) => {
            this.settings = resp;
            this.render();
        });
    },

    render: function () {
        this.$el.html(template({
            settings: this.settings
        }));
        this.breadcrumb.setElement(this.$('.g-config-breadcrumb-container')).render();
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
            this.$('#g-hashsum-download-error-message').text(
                resp.responseJSON.message);
        });
    }
});

export default ConfigView;
