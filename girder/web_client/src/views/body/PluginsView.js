import $ from 'jquery';
import _ from 'underscore';
// Bootstrap tooltip is required by popover
import 'bootstrap/js/tooltip';
import 'bootstrap/js/popover';

import events from '@girder/core/events';
import router from '@girder/core/router';
import View from '@girder/core/views/View';
import { confirm } from '@girder/core/dialog';
import { getPluginConfigRoute } from '@girder/core/utilities/PluginUtils';
import { restartServer } from '@girder/core/server';
import { restRequest, cancelRestRequests } from '@girder/core/rest';

import PluginFailedNoticeTemplate from '@girder/core/templates/widgets/pluginFailedNotice.pug';
import PluginsTemplate from '@girder/core/templates/body/plugins.pug';

import '@girder/core/utilities/jquery/girderEnable';
import '@girder/core/stylesheets/body/plugins.styl';

import 'bootstrap-switch'; // /dist/js/bootstrap-switch.js',
import 'bootstrap-switch/dist/css/bootstrap3/bootstrap-switch.css';

/**
 * This is the plugin management page for administrators.
 */
var PluginsView = View.extend({
    events: {
        'click a.g-plugin-config-link': function (evt) {
            var route = $(evt.currentTarget).attr('g-route');
            router.navigate(route, { trigger: true });
        },
        'click .g-restart': function (e) {
            confirm({
                text: `Are you sure you want to restart the server? This will interrupt all running tasks for all users.`,
                yesText: 'Restart',
                confirmCallback: function () {
                    $(e.currentTarget).girderEnable(false);
                    restartServer()
                        .done(() => {
                            events.trigger('g:alert', {
                                text: 'Server restarted successfully',
                                type: 'success',
                                duration: 3000
                            });
                        })
                        .always(() => {
                            // Re-enable the button whether the chain succeeds or fails, though if
                            // it succeeds, the page will probably be refreshed
                            $(e.currentTarget).girderEnable(true);
                        });
                }
            });
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        if (settings.all && settings.enabled) {
            this.cherrypyServer = (_.has(settings, 'cherrypyServer') ? settings.cherrypyServer : true);
            this.enabled = settings.enabled;
            this.allPlugins = settings.all;
            this.failed = _.has(settings, 'failed') ? settings.failed : null;
            this.render();
        } else {
            const promises = [
                restRequest({
                    url: 'system/plugins',
                    method: 'GET'
                }).then((resp) => resp),
                restRequest({
                    url: 'system/configuration',
                    method: 'GET',
                    data: {
                        section: 'server',
                        key: 'cherrypy_server'
                    }
                }).then((resp) => resp)
            ];

            // Fetch the plugin list
            $.when(...promises).done((plugins, cherrypyServer) => {
                this.cherrypyServer = cherrypyServer;
                this.enabled = plugins.enabled;
                this.allPlugins = plugins.all;
                this.failed = plugins.failed;
                this.render();
            }).fail(() => {
                router.navigate('/', { trigger: true });
            });
        }
    },

    render: function () {
        _.each(this.allPlugins, function (info, name) {
            if (_.contains(this.enabled, name)) {
                info.enabled = true;
                info.configRoute = getPluginConfigRoute(name);
            }

            if (this.failed && _.has(this.failed, name)) {
                info.failed = this.failed[name];
            }
        }, this);

        this.$el.html(PluginsTemplate({
            cherrypyServer: this.cherrypyServer,
            allPlugins: this._sortPlugins(this.allPlugins)
        }));

        this.$('.g-plugin-switch').bootstrapSwitch()
            .off('switchChange.bootstrapSwitch')
            .on('switchChange.bootstrapSwitch', (event, state) => {
                var plugin = $(event.currentTarget).attr('key');
                if (state === true) {
                    this.enabled.push(plugin);
                } else {
                    var idx;
                    while ((idx = this.enabled.indexOf(plugin)) >= 0) {
                        this.enabled.splice(idx, 1);
                    }
                }
                this.$('button.g-restart').addClass('btn-danger');

                if (this.cherrypyServer) {
                    this.$('.g-plugin-restart-text').addClass('show');
                }

                if (!this.cherrypyServer && !_.has(this, 'displayedCherrypyNotification')) {
                    this.displayedCherrypyNotification = true;

                    events.trigger('g:alert', {
                        text: `Enabling and disabling plugins might not take effect until the system administrator has restarted Girder.`,
                        type: 'info',
                        timeout: 5000,
                        icon: 'info'
                    });
                }

                this._updatePlugins();
            });
        this.$('.g-plugin-list-item-failed-notice').popover({
            container: this.$el,
            template: PluginFailedNoticeTemplate()
        });
        this.$('.g-plugin-list-item-failed-notice').each(function () {
            $(this).attr('title', $(this).attr('native-title'));
        });

        return this;
    },

    _sortPlugins: function (plugins) {
        /* Sort a dictionary of plugins alphabetically so that the appear in a
         * predictable order to the user.
         *
         * @param plugins: a dictionary to sort.  Each entry has a .name
         *                 attribute used for sorting.
         * @returns sortedPlugins: the sorted list. */
        var sortedPlugins = _.map(plugins, function (value, key) {
            return { key: key, value: value };
        });
        sortedPlugins.sort(function (a, b) {
            return a.value.name.localeCompare(b.value.name);
        });
        return sortedPlugins;
    },

    _updatePlugins: function () {
        // Remove any missing plugins from the enabled list. Can happen
        // if the directory of an enabled plugin disappears.
        this.enabled = _.intersection(this.enabled, _.keys(this.allPlugins));

        restRequest({
            url: 'system/plugins',
            method: 'PUT',
            data: {
                plugins: JSON.stringify(this.enabled)
            }
        }).done((resp) => {
            this.enabled = resp.value;

            _.each(this.enabled, function (plugin) {
                this.$('.g-plugin-switch[key="' + plugin + '"]')
                    .attr('checked', 'checked').bootstrapSwitch('state', true, true);
            }, this);
        }); // TODO acknowledge?
    }
});

export default PluginsView;
