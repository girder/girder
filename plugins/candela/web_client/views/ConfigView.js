import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';

import ConfigViewTemplate from '../templates/configView.pug';

var ConfigView = View.extend({
    initialize: function (settings) {
        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'Candela file visualizer',
            parentView: this
        });
        this.render();
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());
        this.breadcrumb.setElement(this.$('.g-config-breadcrumb-container')).render();
        return this;
    }
});

export default ConfigView;
