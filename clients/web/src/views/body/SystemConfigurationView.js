/**
 * The system config page for administrators.
 */
girder.views.SystemConfigurationView = girder.View.extend({
    events: {
        'submit .g-settings-form': function (event) {
            event.preventDefault();
            this.$('.g-submit-settings').addClass('disabled');
            this.$('#g-settings-error-message').empty();

            var settings = _.map(this.settingsKeys, function (key) {
                return {
                    key: key,
                    value: this.$('#g-' + key.replace(/[_.]/g, '-')).val() || null
                };
            }, this);

            girder.restRequest({
                type: 'PUT',
                path: 'system/setting',
                data: {
                    list: JSON.stringify(settings)
                },
                error: null
            }).done(_.bind(function () {
                this.$('.g-submit-settings').removeClass('disabled');
                girder.events.trigger('g:alert', {
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
        }
    },

    initialize: function () {
        girder.cancelRestRequests('fetch');

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
            'core.user_default_folders'
        ];
        this.settingsKeys = keys;
        girder.restRequest({
            path: 'system/setting',
            type: 'GET',
            data: {
                list: JSON.stringify(keys),
                default: 'none'
            }
        }).done(_.bind(function (resp) {
            this.settings = resp;
            girder.restRequest({
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
        this.$el.html(girder.templates.systemConfiguration({
            settings: this.settings,
            defaults: this.defaults,
            JSON: window.JSON
        }));

        this.$('input[title]').tooltip({
            container: this.$el,
            animation: false,
            delay: {show: 200}
        });

        this.searchWidget = new girder.views.SearchFieldWidget({
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
                    girder.events.trigger('g:alert', {
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
                    girder.events.trigger('g:alert', {
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

girder.router.route('settings', 'settings', function () {
    girder.events.trigger('g:navigateTo', girder.views.SystemConfigurationView);
});
