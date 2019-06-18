import $ from 'jquery';
import _ from 'underscore';

import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import { getApiRoot, restRequest } from '@girder/core/rest';
import events from '@girder/core/events';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit .g-oauth-provider-form': function (event) {
            event.preventDefault();
            var providerId = $(event.target).attr('provider-id');
            this.$('#g-oauth-provider-' + providerId + '-error-message').empty();

            this._saveSettings(providerId, [{
                key: 'oauth.' + providerId + '_client_id',
                value: this.$('#g-oauth-provider-' + providerId + '-client-id').val().trim()
            }, {
                key: 'oauth.' + providerId + '_client_secret',
                value: this.$('#g-oauth-provider-' + providerId + '-client-secret').val().trim()
            }]);
        },

        'change .g-ignore-registration-policy': function (event) {
            restRequest({
                method: 'PUT',
                url: 'system/setting',
                data: {
                    key: 'oauth.ignore_registration_policy',
                    value: $(event.target).is(':checked')
                }
            }).done(() => {
                events.trigger('g:alert', {
                    icon: 'ok',
                    text: 'Setting saved.',
                    type: 'success',
                    timeout: 3000
                });
            });
        }
    },

    initialize: function () {
        this.providers = [{
            id: 'google',
            name: 'Google',
            icon: 'gplus',
            hasAuthorizedOrigins: true,
            instructions: 'Client IDs and secret keys are managed in the Google ' +
                          'Developer Console. When creating your client ID there, ' +
                          'use the following values:'
        }, {
            id: 'globus',
            name: 'Globus',
            icon: 'globe',
            hasAuthorizedOrigins: false,
            instructions: 'Client IDs and secret keys are managed in the Google ' +
                          'Developer Console. When creating your client ID there, ' +
                          'use the following values:'
        }, {
            id: 'github',
            name: 'GitHub',
            icon: 'github-circled',
            hasAuthorizedOrigins: false,
            instructions: 'Client IDs and secret keys are managed in the ' +
                          'Applications page of your GitHub account settings. ' +
                          'Use the following as the authorization callback URL:'
        }, {
            id: 'bitbucket',
            name: 'Bitbucket',
            icon: 'bitbucket',
            hasAuthorizedOrigins: false,
            instructions: 'Client IDs and secret keys are managed in the ' +
                          'Applications page of your Bitbucket account settings. ' +
                          'Use the following as the authorization callback URL:'
        }, {
            id: 'linkedin',
            name: 'LinkedIn',
            icon: 'linkedin',
            hasAuthorizedOrigins: false,
            instructions: 'Client IDs and secret keys are managed at the ' +
                          'Applications page of the LinkedIn Developers site. ' +
                          'Select the "r_basicprofile" and "r_emailaddress" ' +
                          'Default Application Permissions, and use the ' +
                          'following as an OAuth 2.0 Authorized Redirect URL:'
        }, {
            id: 'box',
            name: 'Box',
            icon: 'box',
            hasAuthorizedOrigins: false,
            instructions: 'Client IDs and secret keys are managed in the Box ' +
                          'Developer Services page. When creating your client ID ' +
                          'there, use the following as the authorization callback URL:'
        }];
        this.providerIds = _.pluck(this.providers, 'id');

        var settingKeys = ['oauth.ignore_registration_policy'];
        _.each(this.providerIds, function (id) {
            settingKeys.push('oauth.' + id + '_client_id');
            settingKeys.push('oauth.' + id + '_client_secret');
        }, this);

        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settingKeys)
            }
        }).done((resp) => {
            this.settingVals = resp;
            this.render();
        });
    },

    render: function () {
        var origin = window.location.protocol + '//' + window.location.host,
            _apiRoot = getApiRoot();

        if (_apiRoot.substring(0, 1) !== '/') {
            _apiRoot = '/' + _apiRoot;
        }

        this.$el.html(ConfigViewTemplate({
            origin: origin,
            apiRoot: _apiRoot,
            providers: this.providers
        }));

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'OAuth login',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        if (this.settingVals) {
            _.each(this.providerIds, function (id) {
                this.$('#g-oauth-provider-' + id + '-client-id').val(
                    this.settingVals['oauth.' + id + '_client_id']);
                this.$('#g-oauth-provider-' + id + '-client-secret').val(
                    this.settingVals['oauth.' + id + '_client_secret']);
            }, this);

            var checked = this.settingVals['oauth.ignore_registration_policy'];
            this.$('.g-ignore-registration-policy').attr('checked', checked ? 'checked' : null);
        }

        return this;
    },

    _saveSettings: function (providerId, settings) {
        settings.push({
            key: 'oauth.providers_enabled',
            value: _.filter(this.providerIds, function (id) {
                return !!this.$('#g-oauth-provider-' + id + '-client-id').val();
            }, this)
        });

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
            this.$('#g-oauth-provider-' + providerId + '-error-message').text(
                resp.responseJSON.message);
        });
    }
});

export default ConfigView;
