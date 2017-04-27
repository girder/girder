import _ from 'underscore';

import $ from 'jquery';
import 'jquery-ui/themes/base/core.css';
import 'jquery-ui/themes/base/theme.css';
import 'jquery-ui/themes/base/sortable.css';
import 'jquery-ui/ui/core';
import 'jquery-ui/ui/widgets/sortable';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import { restRequest } from 'girder/rest';
import events from 'girder/events';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit .g-ldap-server-form': function (event) {
            event.preventDefault();
            this.$('#g-ldap-servers-error-message').empty();
            this._saveSettings();
        },
        'click .g-remove-ldap-server': function (event) {
            var idx = $(event.currentTarget).attr('idx');

            // Remove this server from the DOM.
            this.servers.splice(idx, 1);
            this.render();
        },
        'click .g-ldap-add-server': function () {
            this.servers.push({ collapsedClass: 'in' });
            this.render();
        }
    },

    initialize: function () {
        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                key: 'ldap.servers'
            }
        }).done(resp => {
            if (resp.length) {
                this.servers = resp;
            } else {
                // Show an empty server for the user to fill in.
                this.servers = [{ collapsedClass: 'in' }];
            }
            this.render();
        }, this);

        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'LDAP login',
            parentView: this
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            servers: this.servers
        }));

        this.breadcrumb.setElement(this.$('.g-config-breadcrumb-container')).render();

        this.$('.g-ldap-server-accordion').sortable({
            stop: () => {
                _.each(this.$('.g-ldap-server-accordion').children(), (child, i) => {
                    // Record new position of server in the list
                    this.servers[$(child).attr('idx')].position = i;
                });
            }
        });

        return this;
    },

    _saveSettings: function () {
        const servers = [];
        const fieldsToSave = ['uri', 'bindName', 'baseDn', 'password', 'searchField'];

        // Whether or not the user modified the priority order of the servers.
        const hasPosition = _.has(this.servers[0], 'position');

        _.each(this.servers, (oldServer, i) => {
            const server = {};
            _.each(fieldsToSave, field => {
                const val = this.$(`#g-ldap-server-${i}-${field}`).val();
                if (val) {
                    server[field] = val;
                }
                if (hasPosition) {
                    server.position = oldServer.position;
                }
            });
            servers.push(server);
        });

        if (hasPosition) {
            // Sort by position before serializing.
            servers.sort((a, b) => a.position - b.position);
            _.each(servers, server => {
                delete server.position;
            });
        }

        restRequest({
            type: 'PUT',
            path: 'system/setting',
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
        }).error(resp => {
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    }
});

export default ConfigView;
