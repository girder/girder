import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import Model from 'girder/models/Model';
import Collection from 'girder/collections/Collection';
import events from 'girder/events';
import { renderMarkdown } from 'girder/misc';
import { restRequest } from 'girder/rest';

import PluginConfigTemplate from 'girder/templates/layout/pluginConfig.pug';
import 'girder/stylesheets/layout/pluginConfig.styl';
import PluginSettingTemplate from 'girder/templates/layout/pluginSetting.pug';

const SettingModel = Model.extend({
    idAttribute: 'key'

    // TODO: validate that the key contains only alphanumeric, dots, and underscores

    // TODO: add methods for individual fetch, save, destroy
});

const SettingCollection = Collection.extend({
    model: SettingModel,

    fetch: function (options) {
        const settingList = this.map((model) => model.get('key'));
        return $.when(
            restRequest({
                type: 'GET',
                path: 'system/setting',
                data: {
                    list: JSON.stringify(settingList),
                    default: 'none'
                }
                // Use '.then' to ensure only the first argument is passed as the fulfilment value
            }).then((resp) => resp),
            restRequest({
                type: 'GET',
                path: 'system/setting',
                data: {
                    list: JSON.stringify(settingList),
                    default: 'default'
                }
            }).then((resp) => resp)
        )
            .then((valueResp, defaultResp) => {
                const combinedResp = this.map((model) => ({
                    key: model.get('key'),
                    value: valueResp[model.get('key')],
                    'default': defaultResp[model.get('key')]
                }));

                // This is a re-implementation of the basic logic from Backbone.Collection.fetch
                options = _.extend({parse: true}, options);
                const method = options.reset ? 'reset' : 'set';
                this[method](combinedResp, options);
                this.trigger('sync', this, combinedResp, options);

                return undefined;
            }, () => {
                // TODO: transform error messages
                throw undefined;
            });
    },

    saveAll: function () {
        const settingList = this.map((model) => ({
            key: model.get('key'),
            // TODO: if the server sends down an empty string, we will send it back (not null) if
            // if the user does not edit the field, but send back null if they do edit it; this
            // should probably be fixed with some migration logic on the server (maybe in .get)
            value: model.get('value')
        }));
        return restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settingList)
            },
            error: null
        });
        // TODO: maybe a failure extracts the error message to set directly as the rejection value
    }
});

const PluginSettingWidget = View.extend({
    events: {
        'change input': function () {
            // Set empty string to null, which will also unset it on the server
            const value = this.$('input').val().trim() || null;
            this.model.set('value', value);
            // Sync the trimmed string back to the DOM
            this.$('input').val(value);
        }
    },

    initialize: function () {
        this.listenTo(this.model, 'change:value', this._renderValue);
        this.listenTo(this.model, 'change:default', this.render);
        // All other SettingModel attributes should never change
    },

    render: function () {
        this.$el.html(PluginSettingTemplate({
            setting: this.model,
            renderMarkdown: renderMarkdown
        }));
        this._renderValue();
        return this;
    },

    _renderValue: function () {
        this.$('input').val(this.model.get('value'));
    }
});

const AbstractPluginConfigView = View.extend({
    events: {
        'submit #g-plugin-config-form': function (event) {
            event.preventDefault();
            this._saveSettings();
        }
    },
    initialize: function (settings) {
        // TODO: can we fetch pluginName from the API listing?
        this.pluginName = settings.pluginName;
        this.description = settings.description;
        this.collection = new SettingCollection(settings.settings);

        this.collection.fetch()
            .done(() => {
                this.render();
            });
    },

    render: function () {
        this.$el.html(PluginConfigTemplate({
            description: this.description,
            renderMarkdown: renderMarkdown
        }));

        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            el: this.$('#g-plugin-config-breadcrumb'),
            parentView: this,
            pluginName: this.pluginName
        }).render();

        this.settingWidgets = this.collection.map((model) => {
            const settingWidget = new PluginSettingWidget({
                parentView: this,
                model: model
            });
            settingWidget.$el.appendTo(this.$('.g-plugin-config-settings'));
            settingWidget.render();
            return settingWidget;
        });

        return this;
    },

    _saveSettings: function () {
        this.$('#g-plugin-config-error-message').empty();
        // Disable all input fields and the submit button
        this.$('input').girderEnable(false);

        this.collection.saveAll()
            .done(() => {
                events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Settings saved.',
                    type: 'success',
                    timeout: 4000
                });
            })
            .fail((resp) => {
                this.$('#g-celery-jobs-error-message').text(resp.responseJSON.message);
            })
            .then(() => {
                // Refresh the settings, in case the server validator changed them
                return this.collection.fetch();
            })
            .always(() => {
                this.$('input').girderEnable(true);
            });
    }
});

export default AbstractPluginConfigView;
