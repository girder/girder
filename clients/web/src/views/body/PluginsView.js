/**
 * This is the plugin management page for administrators.
 */
girder.views.PluginsView = girder.View.extend({
    events: {
        'click a.g-plugin-config-link': function (evt) {
            var route = $(evt.currentTarget).attr('g-route');
            girder.router.navigate(route, {trigger: true});
        }
    },

    initialize: function (settings) {
        if (settings.all && settings.enabled) {
            this.enabled = settings.enabled;
            this.allPlugins = settings.all;
            this.render();
        }
        else {
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
        }, this);

        this.$el.html(jade.templates.plugins({
            allPlugins: this.allPlugins
        }));

        var view = this;
        this.$('.g-plugin-switch').bootstrapSwitch()
            .off('switchChange.bootstrapSwitch')
            .on('switchChange.bootstrapSwitch', function (event, state) {
                var plugin = $(event.currentTarget).attr('key');
                if (state === true) {
                    view.enabled.push(plugin);
                }
                else {
                    var idx;
                    while ((idx = view.enabled.indexOf(plugin)) >= 0) {
                        view.enabled.splice(idx, 1);
                    }
                }
                view._updatePlugins();
            });
        this.$('.g-plugin-config-link').tooltip({
            container: this.$el,
            animation: false,
            placement: 'bottom',
            delay: {show: 100}
        });

        return this;
    },

    _updatePlugins: function () {
        girder.restRequest({
            path: 'system/plugins',
            type: 'PUT',
            data: {
                plugins: JSON.stringify(this.enabled)
            }
        }).done(_.bind(function (resp) {
            // TODO acknowledge?
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
