import $ from 'jquery';
import _ from 'underscore';

import events from 'girder/events';
import router from 'girder/router';
import View from 'girder/views/View';
import { confirm } from 'girder/dialog';
import { getPluginConfigRoute } from 'girder/utilities/PluginUtils';
import { restartServer, rebuildWebClient } from 'girder/server';
import { restRequest, cancelRestRequests } from 'girder/rest';

import PluginFailedNoticeTemplate from 'girder/templates/widgets/pluginFailedNotice.pug';
import PluginsTemplate from 'girder/templates/body/plugins.pug';

import 'girder/utilities/jquery/girderEnable';
import 'girder/stylesheets/body/plugins.styl';

import 'bootstrap/js/tooltip';
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
        'click .g-rebuild-and-restart': function (e) {
            confirm({
                text: `Are you sure you want to rebuild web code and restart the server? This will interrupt all running tasks for all users.`,
                yesText: 'Restart',
                confirmCallback: function () {
                    $(e.currentTarget).girderEnable(false);
                    rebuildWebClient()
                        .then(() => {
                            events.trigger('g:alert', {
                                text: 'Web client code built successfully',
                                type: 'success',
                                duration: 3000
                            });

                            return restartServer();
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
            this.cherrypyServer = (_.has(settings, 'cherrypyServer')
                                   ? settings.cherrypyServer : true);
            this.enabled = settings.enabled;
            this.allPlugins = settings.all;
            this.failed = _.has(settings, 'failed') ? settings.failed : null;
            this.render();
        } else {
            const promises = [
                restRequest({
                    path: 'system/plugins',
                    type: 'GET'
                }).then((resp) => resp),
                restRequest({
                    path: 'system/configuration',
                    type: 'GET',
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
            info.unmetDependencies = this._unmetDependencies(info);
            if (!_.isEmpty(info.unmetDependencies)) {
                // Disable any plugins with unmet dependencies.
                this.enabled = _.without(this.enabled, name);
            }

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
                this.$('button.g-rebuild-and-restart').addClass('btn-danger');

                if (this.cherrypyServer) {
                    this.$('.g-plugin-rebuild-restart-text').addClass('show');
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
        this.$('.g-plugin-config-link').tooltip({
            container: this.$el,
            animation: false,
            placement: 'bottom',
            delay: { show: 100 }
        });
        this.$('.g-plugin-list-item-experimental-notice').tooltip({
            container: this.$el,
            animation: false,
            delay: { show: 100 }
        });
        this.$('.g-plugin-list-item-failed-notice').tooltip({
            title: 'Click to see traceback',
            container: this.$el,
            animation: false,
            delay: { show: 100 }
        });
        this.$('.g-plugin-list-item-failed-notice').popover({
            container: this.$el,
            template: PluginFailedNoticeTemplate()
        });

        return this;
    },

    /**
     * Takes a plugin object and determines if it has any top level
     * unmet dependencies.
     *
     * Given A depends on B, and B depends on C, and C is not present:
     * A will have unmet dependencies of ['B'], and B will have unmet dependencies
     * of ['C'].
     **/
    _unmetDependencies: function (plugin) {
        return _.reject(plugin.dependencies, function (pluginName) {
            return _.has(this.allPlugins, pluginName) &&
                _.isEmpty(this._unmetDependencies(this.allPlugins[pluginName]));
        }, this);
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
            path: 'system/plugins',
            type: 'PUT',
            data: {
                plugins: JSON.stringify(this.enabled)
            }
        }).done(_.bind(function (resp) {
            this.enabled = resp.value;

            _.each(this.enabled, function (plugin) {
                this.$('.g-plugin-switch[key="' + plugin + '"]')
                    .attr('checked', 'checked').bootstrapSwitch('state', true, true);
            }, this);
        }, this));  // TODO acknowledge?
    }
});

export default PluginsView;
