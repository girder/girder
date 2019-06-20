import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit #g-item-licenses-settings-form': function (event) {
            event.preventDefault();

            this.$('#g-item-licenses-error-message').empty();

            this._saveSettings([{
                key: 'item_licenses.licenses',
                value: this.$('#g-item-licenses').val().trim()
            }]);
        },
        'click #g-item-licenses-defaults': function (event) {
            event.preventDefault();

            restRequest({
                method: 'GET',
                url: 'item/licenses',
                data: {
                    'default': true
                }
            }).done((resp) => {
                this.licenses = resp;
                this.render();
            });
        }
    },

    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['item_licenses.licenses'])
            }
        }).done((resp) => {
            this.licenses = resp['item_licenses.licenses'];
            this.render();
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            licenses: JSON.stringify(this.licenses, null, 4)
        }));

        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'Item licenses',
            el: this.$('.g-config-breadcrumb-container'),
            parentView: this
        }).render();

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
                timeout: 3000
            });
        }).fail((resp) => {
            this.$('#g-item-licenses-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
