/**
 * This is the plugin management page for administrators.
 */
girder.views.PluginsView = girder.View.extend({
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
                confirmCallback: girder.restartServer
            };
            girder.confirm(params);
        }
    },

    initialize: function (settings) {
        girder.cancelRestRequests('fetch');
        if (settings.all && settings.enabled) {
            this.enabled = settings.enabled;
            this.allPlugins = settings.all;
            this.render();
        } else {
            // Fetch the plugin list
            girder.restRequest({
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
        _.each(this.allPlugins, function (info, name) {
            if (this.enabled.indexOf(name) >= 0) {
                info.enabled = true;
                info.configRoute = girder.getPluginConfigRoute(name);
            }

            info.meetsDependencies = this._meetsDependencies(info);
        }, this);

        this.$el.html(girder.templates.plugins({
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
                girder.pluginsChanged = true;
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
        if (girder.pluginsChanged) {
            $('.g-plugin-restart').addClass('g-plugin-restart-show');
        }

        return this;
    },

    /**
     * Takes a plugin object and recursively determines if it fulfills
     * dependencies. Meaning, its dependencies exist in this.allPlugins.
     **/
    _meetsDependencies: function (plugin) {
        return _.every(plugin.dependencies, function (pluginName) {
            return _.has(this.allPlugins, pluginName) &&
                this._meetsDependencies(this.allPlugins[pluginName]);
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
        girder.restRequest({
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
        }, this)).error(_.bind(function () {
            // TODO acknowledge?
        }, this));
    }
});

girder.router.route('plugins', 'plugins', function () {
    // Fetch the plugin list
    girder.restRequest({
        path: 'system/plugins',
        type: 'GET'
    }).done(_.bind(function (resp) {
        girder.events.trigger('g:navigateTo', girder.views.PluginsView, resp);
    }, this)).error(_.bind(function () {
        girder.events.trigger('g:navigateTo', girder.views.UsersView);
    }, this));
});
