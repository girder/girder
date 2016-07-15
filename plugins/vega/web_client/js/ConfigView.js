import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import { events } from 'girder/events';
import router from 'girder/router';

girder.views.vega_ConfigView = View.extend({
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

router.route('plugins/vega/config', 'vegaConfig', function () {
    events.trigger('g:navigateTo', girder.views.vega_ConfigView);
});

girder.exposePluginConfig('vega', 'plugins/vega/config');
