import _ from 'underscore';
import sortable from 'sortablejs';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import { restRequest } from 'girder/rest';
import events from 'girder/events';

import template from '../templates/configView.pug';
import newServerTemplate from '../templates/newServerTemplate.pug';
import '../stylesheets/configView.styl';

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
                server: {collapsedClass: 'in'},
                index: this.$('.g-ldap-server-panel').length
            }));
        },
        'input .g-uri-input': function (event) {
            const field = $(event.currentTarget);
            field.parents('.panel').find('.g-ldap-server-title').text(field.val());
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
        sortable.create(this.$('.g-ldap-server-accordion')[0]);
        return this;
    },

    _saveSettings: function () {
        const servers = _.map(this.$('.g-ldap-server-panel'), panel => {
            const server = {};
            _.each(FIELDS, field => {
                server[field] = $(panel).find(`input[name="${field}"]`).val();
            });
            return server;
        });

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
