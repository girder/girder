var $               = require('jquery');
var _               = require('underscore');

var girder          = require('girder/init');
var Events          = require('girder/events');
var MiscFunctions   = require('girder/utilities/MiscFunctions');
var PluginsTemplate = require('girder/templates/body/plugins.jade');
var Rest            = require('girder/rest');
var UsersView       = require('girder/views/body/UsersView');
var View            = require('girder/view');

require('bootstrap-switch'); // /dist/js/bootstrap-switch.js',
require('bootstrap/js/tooltip');

/**
 * This is the plugin management page for administrators.
 */
var PluginsView = View.extend({
    events: {
        'click a.g-plugin-config-link': function (evt) {
            var route = $(evt.currentTarget).attr('g-route');
            girder.router.navigate(route, {trigger: true});
        },
        'click .g-plugin-restart-button': function () {
            var params = {
                text: 'Are you sure you want to restart the server?  This ' +
                      'will interrupt all running tasks for all users.',
                yesText: 'Restart',
                confirmCallback: MiscFunctions.restartServer
            };
            MiscFunctions.confirm(params);
        }
    },

    initialize: function (settings) {
        Rest.cancelRestRequests('fetch');
        if (settings.all && settings.enabled) {
            this.enabled = settings.enabled;
            this.allPlugins = settings.all;
            this.render();
        } else {
            // Fetch the plugin list
            Rest.restRequest({
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
                info.configRoute = MiscFunctions.getPluginConfigRoute(name);
            }
        }, this);

        this.$el.html(PluginsTemplate({
            allPlugins: this._sortPlugins(this.allPlugins)
        }));

        var view = this;
        this.$('.g-plugin-switch').bootstrapSwitch({
            offText: '&nbsp;'
        }).off('switchChange.bootstrapSwitch')
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
        var sortedPlugins = [];
        _.each(plugins, function (value, key) {
            sortedPlugins.push({key: key, value: value});
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

        Rest.restRequest({
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

module.exports = PluginsView;

girder.router.route('plugins', 'plugins', function () {
    // Fetch the plugin list
    Rest.restRequest({
        path: 'system/plugins',
        type: 'GET'
    }).done(_.bind(function (resp) {
        Events.trigger('g:navigateTo', PluginsView, resp);
    }, this)).error(_.bind(function () {
        Events.trigger('g:navigateTo', UsersView);
    }, this));
});
