import _ from 'underscore';

import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest, cancelRestRequests } from 'girder/rest';
import { restartServerPrompt } from 'girder/server';

import SystemConfigurationTemplate from 'girder/templates/body/systemConfiguration.pug';

import 'girder/stylesheets/body/systemConfig.styl';

import 'bootstrap/js/collapse';
import 'bootstrap/js/tooltip';

/**
 * The system config page for administrators.
 */
var SystemConfigurationView = View.extend({
    events: {
        'submit .g-settings-form': function (event) {
            event.preventDefault();
            this.$('.g-submit-settings').addClass('disabled');
            this.$('#g-settings-error-message').empty();

            var settings = _.map(this.settingsKeys, function (key) {
                if (key === 'core.route_table') {
                    return {
                        key: key,
                        value: _.object(_.map($('.g-core-route-table'), function (el) {
                            return [$(el).data('webroot-name'), $(el).val()];
                        }))
                    };
                }

                return {
                    key: key,
                    value: this.$('#g-' + key.replace(/[_.]/g, '-')).val() || null
                };
            }, this);

            restRequest({
                type: 'PUT',
                path: 'system/setting',
                data: {
                    list: JSON.stringify(settings)
                },
                error: null
            }).done(_.bind(function () {
                this.$('.g-submit-settings').removeClass('disabled');
                events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Settings saved.',
                    type: 'success',
                    timeout: 4000
                });
            }, this)).error(_.bind(function (resp) {
                this.$('.g-submit-settings').removeClass('disabled');
                this.$('#g-settings-error-message').text(resp.responseJSON.message);
            }, this));
        },
        'click .g-edit-collection-create-policy': function () {
            this.collectionCreateAccessWidget.render();
        },
        'click #g-restart-server': restartServerPrompt
    },

    initialize: function () {
        cancelRestRequests('fetch');

        var keys = [
            'core.cookie_lifetime',
            'core.email_from_address',
            'core.email_host',
            'core.registration_policy',
            'core.email_verification',
            'core.smtp_host',
            'core.smtp.port',
            'core.smtp.encryption',
            'core.smtp.username',
            'core.smtp.password',
            'core.upload_minimum_chunk_size',
            'core.cors.allow_origin',
            'core.cors.allow_methods',
            'core.cors.allow_headers',
            'core.add_to_group_policy',
            'core.collection_create_policy',
            'core.user_default_folders',
            'core.route_table'
        ];
        this.settingsKeys = keys;
        restRequest({
            path: 'system/setting',
            type: 'GET',
            data: {
                list: JSON.stringify(keys),
                default: 'none'
            }
        }).done(_.bind(function (resp) {
            this.settings = resp;
            restRequest({
                path: 'system/setting',
                type: 'GET',
                data: {
                    list: JSON.stringify(keys),
                    default: 'default'
                }
            }).done(_.bind(function (resp) {
                this.defaults = resp;
                this.render();
            }, this));
        }, this));
    },

    render: function () {
        this.$el.html(SystemConfigurationTemplate({
            settings: this.settings,
            defaults: this.defaults,
            routes: this.settings['core.route_table'] || this.defaults['core.route_table'],
            routeKeys: _.sortBy(_.keys(this.settings['core.route_table'] ||
                                       this.defaults['core.route_table']),
                                function (a) {
                                    return a.indexOf('core_') === 0 ? -1 : 0;
                                }),
            JSON: window.JSON
        }));

        this.$('input[title]').tooltip({
            container: this.$el,
            animation: false,
            delay: {show: 200}
        });

        this.searchWidget = new SearchFieldWidget({
            el: this.$('.g-collection-create-policy-container .g-search-container'),
            parentView: this,
            types: ['user', 'group'],
            placeholder: 'Add a user or group...',
            settingValue: this.settings['core.collection_create_policy'] ||
                               this.defaults['core.collection_create_policy']
        }).on('g:resultClicked', function (result) {
            var settingValue = null;

            try {
                settingValue = JSON.parse(this.$('#g-core-collection-create-policy').val());
                this.$('#g-settings-error-message').empty();
            } catch (err) {
                this.$('#g-settings-error-message').text('Collection creation policy must be a JSON object.');
                this.searchWidget.resetState();
                return this;
            }
            this.searchWidget.resetState();

            if (result.type === 'user') {
                settingValue.users = settingValue.users || [];
                if (!_.contains(settingValue.users, result.id)) {
                    settingValue.users.push(result.id);
                } else {
                    events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'User already exists in current policy.',
                        type: 'warning',
                        timeout: 4000
                    });
                }
            } else if (result.type === 'group') {
                settingValue.groups = settingValue.groups || [];
                if (!_.contains(settingValue.groups, result.id)) {
                    settingValue.groups.push(result.id);
                } else {
                    events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'Group already exists in current policy.',
                        type: 'warning',
                        timeout: 4000
                    });
                }
            }

            this.$('#g-core-collection-create-policy').val(
                JSON.stringify(settingValue, null, 4));
        }, this).render();

        return this;
    }
});

export default SystemConfigurationView;

