import router from 'girder/router';
import View from 'girder/views/View';

import PluginConfigBreadcrumbTemplate from 'girder/templates/widgets/pluginConfigBreadcrumb.pug';

/**
 * This widget provides a consistent breadcrumb to be displayed on the admin
 * configuration pages for plugins.
 */
var PluginConfigBreadcrumbWidget = View.extend({
    events: {
        'click a.g-admin-console-link': function () {
            router.navigate('admin', {trigger: true});
        },
        'click a.g-plugins-link': function () {
            router.navigate('plugins', {trigger: true});
        }
    },

    initialize: function (settings) {
        this.pluginName = settings.pluginName;
    },

    render: function () {
        this.$el.html(PluginConfigBreadcrumbTemplate({
            pluginName: this.pluginName
        }));

        return this;
    }
});

export default PluginConfigBreadcrumbWidget;
