import $ from 'jquery';
import _ from 'underscore';
import sortable from 'sortablejs';

import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';

import template from '../templates/configView.pug';
import newServerTemplate from '../templates/newServerTemplate.pug';
import '../stylesheets/configView.styl';
import '@girder/core/utilities/jquery/girderEnable';

const FIELDS = ['uri', 'bindName', 'baseDn', 'password', 'searchField'];

var ConfigView = View.extend({
    events: {
        'submit .g-ldap-server-form': function (event) {
            event.preventDefault();
            this.$('#g-ldap-servers-error-message').empty();
            this._saveSettings();
        },
        'click .g-remove-ldap-server': function (event) {
            $(event.currentTarget).parents('.panel').remove();
        },
        'click .g-ldap-add-server': function () {
            this.$('.g-ldap-server-accordion').append(newServerTemplate({
                server: { collapsedClass: 'in' },
                index: this.$('.g-ldap-server-panel').length
            }));
        },
        'input .g-uri-input': function (event) {
            const field = $(event.currentTarget);
            field.parents('.panel').find('.g-ldap-server-title').text(field.val());
        },
        'click .g-ldap-test': function (event) {
            const btn = $(event.currentTarget);
            const idx = btn.attr('index');
            const uri = this.$(`#g-ldap-server-${idx}-uri`).val();
            const bindName = this.$(`#g-ldap-server-${idx}-bindName`).val();
            const password = this.$(`#g-ldap-server-${idx}-password`).val();

            restRequest({
                url: 'system/ldap_server/status',
                method: 'GET',
                data: {
                    uri,
                    bindName,
                    password
                }
            }).done((resp) => {
                btn.girderEnable(true);
                if (resp.connected) {
                    this.$(`#g-ldap-server-${idx}-conn-ok`).removeClass('hide');
                } else {
                    this.$(`#g-ldap-server-${idx}-conn-fail`).removeClass('hide')
                        .find('.g-msg').text(resp.error);
                }
            });

            btn.girderEnable(false);
            this.$(`#g-ldap-server-${idx}-conn-ok`).addClass('hide');
            this.$(`#g-ldap-server-${idx}-conn-fail`).addClass('hide');
        }
    },

    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                key: 'ldap.servers'
            }
        }).done((resp) => {
            this.servers = resp;
            this.render();
        });

        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'LDAP login',
            parentView: this
        });
    },

    render: function () {
        this.$el.html(template({
            servers: this.servers
        }));

        this.breadcrumb.setElement(this.$('.g-config-breadcrumb-container')).render();
        sortable.create(this.$('.g-ldap-server-accordion')[0], {
            filter: 'input',
            preventOnFilter: false
        });
        return this;
    },

    _saveSettings: function () {
        const servers = _.map(this.$('.g-ldap-server-panel'), (panel) => {
            const server = {};
            _.each(FIELDS, (field) => {
                server[field] = $(panel).find(`input[name="${field}"]`).val();
            });
            return server;
        });

        this.$('.g-validation-failed-message').empty();

        restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                key: 'ldap.servers',
                value: JSON.stringify(servers)
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
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    }
});

export default ConfigView;
