import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

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
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#g-gravatar-default-image').val(
                resp['gravatar.default_image']
            );
        }, this));
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
        }).done(_.bind(function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).fail(_.bind(function (resp) {
            this.$('#g-gravatar-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

export default ConfigView;
