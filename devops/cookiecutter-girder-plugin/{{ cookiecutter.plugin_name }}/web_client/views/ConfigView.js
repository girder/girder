import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import ConfigViewTemplate from '../templates/configView.pug';

{% set plugin_name_dashed = cookiecutter.plugin_name|replace("_", "-") -%}
var ConfigView = View.extend({
    events: {
        'submit #{{ plugin_name_dashed }}-settings-form': function (event) {
            event.preventDefault();
            this.$('#{{ plugin_name_dashed }}-settings-error-message').empty();

            this._saveSettings([{
                key: '{{ cookiecutter.plugin_name }}.item_metadata',
                value: this.$('#{{ plugin_name_dashed }}-item-metadata').val().trim()
            }]);
        }
    },

    initialize: function () {
        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify([
                    '{{ cookiecutter.plugin_name }}.item_metadata'
                ])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#{{ plugin_name_dashed}}-item-metadata').val(resp['{{ cookiecutter.plugin_name }}.item_metadata']);
        }, this));
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: '{{ cookiecutter.plugin_nice_name }}',
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
            this.$('#{{ plugin_name_dashed }}-settings-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

export default ConfigView;
