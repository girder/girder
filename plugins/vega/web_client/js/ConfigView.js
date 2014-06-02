/**
 * This widget provides a text field that will search any set of data types
 * and show matching results as the user types. Results can be clicked,
 * triggering a callback.
 */
girder.views.Vega_ConfigView = girder.View.extend({
    events: {
        'click a.g-admin-console-link': function () {
            girder.router.navigate('admin', {trigger: true});
        },
        'click a.g-plugins-link': function () {
            girder.router.navigate('plugins', {trigger: true});
        }
    },

    initialize: function (settings) {
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.vega_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Vega File Visualizer',
                el: this.$('.g-config-breadcrumb-container')
            }).render();
        }

        return this;
    }
});

girder.router.route('plugins/vega/config', 'vegaConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.Vega_ConfigView);
});

girder.exposePluginConfig('vega', 'plugins/vega/config');
