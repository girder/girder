import $ from 'jquery';
import _ from 'underscore';

import events from 'girder/events';
import router from 'girder/router';
import View from 'girder/views/View';
import { getPluginConfigRoute } from 'girder/utilities/PluginUtils';
import { restartServerPrompt } from 'girder/server';
import { restRequest, cancelRestRequests } from 'girder/rest';

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
            router.navigate(route, {trigger: true});
        },
        'click .g-plugin-restart-button': restartServerPrompt,
        'click .g-rebuild-web-code': function (e) {
            $(e.currentTarget).girderEnable(false);
            restRequest({
                path: 'system/web_build',
                type: 'POST',
                data: {
                    progress: true
                }
            }).done(() => {
                events.trigger('g:alert', {
                    text: 'Web client code built successfully',
                    type: 'success',
                    duration: 3000
                });
            }).complete(() => {
                $(e.currentTarget).girderEnable(true);
            });
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        if (settings.all && settings.enabled) {
            this.enabled = settings.enabled;
            this.allPlugins = settings.all;
            this.render();
        } else {
            // Fetch the plugin list
            restRequest({
                path: 'system/plugins',
                type: 'GET'
            }).done(_.bind(function (resp) {
                this.enabled = resp.enabled;
                this.allPlugins = resp.all;
                this.render();
            }, this));
        }
    },

    render: function () {
        var pluginsChanged = false;
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
        }, this);

        this.$el.html(PluginsTemplate({
            allPlugins: this._sortPlugins(this.allPlugins)
        }));

        var view = this;
        this.$('.g-plugin-switch').bootstrapSwitch()
          .off('switchChange.bootstrapSwitch')
          .on('switchChange.bootstrapSwitch', function (event, state) {
              var plugin = $(event.currentTarget).attr('key');
              if (state === true) {
                  view.enabled.push(plugin);
              } else {
                  var idx;
                  while ((idx = view.enabled.indexOf(plugin)) >= 0) {
                      view.enabled.splice(idx, 1);
                  }
              }
              pluginsChanged = true;
              $('.g-plugin-restart').addClass('g-plugin-restart-show');
              view._updatePlugins();
          });
        this.$('.g-plugin-config-link').tooltip({
            container: this.$el,
            animation: false,
            placement: 'bottom',
            delay: {show: 100}
        });
        this.$('.g-experimental-notice').tooltip({
            container: this.$el,
            animation: false,
            delay: {show: 100}
        });
        if (pluginsChanged) {
            $('.g-plugin-restart').addClass('g-plugin-restart-show');
        }

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
            return {key: key, value: value};
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
