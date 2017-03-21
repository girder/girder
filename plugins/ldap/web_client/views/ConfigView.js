import _ from 'underscore';

import $ from 'jquery';
import 'jquery-ui/themes/base/core.css';
import 'jquery-ui/themes/base/theme.css';
import 'jquery-ui/themes/base/sortable.css';
import 'jquery-ui/ui/core';
import 'jquery-ui/ui/widgets/sortable';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import { apiRoot, restRequest } from 'girder/rest';
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
        'click .icon-cancel': function (event) {
            event.stopPropagation();
            // Get the index of the server to remove.
            var idx = Number(event.target.id.match(/server-([0-9]+)-remove/)[1]);

            // Remove this server from the DOM.
            this.servers.splice(idx, 1);
            this.render();
        },
        'click #g-ldap-add-server': function (event) {
            this.servers.push({ collapsedClass: 'in' });
            this.render();
        }
    },

    initialize: function () {
        var settingKeys = ['ldap.servers'];
        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settingKeys)
            }
        }).done(_.bind(function (resp) {
            if (resp["ldap.servers"].length > 0) {
                this.servers = resp["ldap.servers"];
            } else {
                // Show an empty server for the user to fill in.
                this.servers = [{ collapsedClass: 'in' }];
            }
            this.render();
        }, this));
    },

    render: function () {
        var origin = window.location.protocol + '//' + window.location.host,
            _apiRoot = apiRoot;

        if (apiRoot.substring(0, 1) !== '/') {
            _apiRoot = '/' + apiRoot;
        }

        this.$el.html(ConfigViewTemplate({
            origin: origin,
            apiRoot: _apiRoot,
            servers: this.servers
        }));

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'LDAP login',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        var view = this;
        $('#g-ldap-server-accordion').sortable({
            stop: function(event, ui) {
                var children = $('#g-ldap-server-accordion').children();
                for (var i = 0; i < children.length; i++) {
                    // Find index of this server.
                    var idx = Number($(children[i]).attr('id').match(/server-([0-9]+)/)[1]);
                    // Record its new position.
                    view.servers[idx].position = i;
                }
            }
        });

        return this;
    },

    _saveSettings: function () {
        var servers = []
        var fieldsToSave = ['uri', 'bindName', 'baseDn', 'password', 'searchField'];

        // Whether or not the user modified the priority order of the servers.
        var hasPosition = this.servers[0].hasOwnProperty('position');

        for (var i = 0; i < this.servers.length; i++) {
            var server = {}
            _.each(fieldsToSave, function (field) {
                var val = this.$('#g-ldap-server-' + i + '-' + field).val();
                if (val) {
                    server[field] = val;
                }
                if (hasPosition) {
                    server.position = this.servers[i].position;
                }
            }, this);
            servers.push(server);
        }

        if (hasPosition) {
            // Sort by position before serializing.
            servers.sort(function(a, b){
                return a.position - b.position;
            });
            for (var i = 0; i < servers.length; i++) {
              delete servers[i].position;
            }
        }

        var settings = [{
            key: 'ldap.servers',
            value: servers
        }];

        restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 3000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-ldap-servers-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

export default ConfigView;
