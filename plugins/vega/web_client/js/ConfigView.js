/**
 * This widget provides a text field that will search any set of data types
 * and show matching results as the user types. Results can be clicked,
 * triggering a callback.
 */
girder.views.vega_ConfigView = girder.View.extend({
    initialize: function (settings) {
        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.vega_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Vega file visualizer',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    }
});

girder.router.route('plugins/vega/config', 'vegaConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.vega_ConfigView);
});

girder.exposePluginConfig('vega', 'plugins/vega/config');
