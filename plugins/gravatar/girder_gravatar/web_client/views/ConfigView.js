import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';

var ConfigView = View.extend({
    events: {
        'submit #g-gravatar-settings-form': function (event) {
            event.preventDefault();
            this.$('#g-gravatar-error-message').empty();

            this._saveSettings([{
                key: 'gravatar.default_image',
                value: this.$('#g-gravatar-default-image').val().trim()
            }]);
        }
    },

    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(['gravatar.default_image'])
            }
        }).done((resp) => {
            this.render();
            this.$('#g-gravatar-default-image').val(
                resp['gravatar.default_image']
            );
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Gravatar portraits',
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
            this.$('#g-gravatar-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
