/**
 * This is the plugin management page for administrators.
 */
girder.views.PluginsView = Backbone.View.extend({
    events: {
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
            }
        }, this);

        this.$el.html(jade.templates.plugins({
            allPlugins: this.allPlugins
        }));

        this.$('.g-plugin-switch').bootstrapSwitch();

        girder.router.navigate('plugins');

        return this;
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
