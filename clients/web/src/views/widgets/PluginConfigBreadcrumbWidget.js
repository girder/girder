/**
 * This widget provides a consistent breadcrumb to be displayed on the admin
 * configuration pages for plugins.
 */
girder.views.PluginConfigBreadcrumbWidget = girder.View.extend({
    events: {
        'click a.g-admin-console-link': function () {
            girder.router.navigate('admin', {trigger: true});
        },
        'click a.g-plugins-link': function () {
            girder.router.navigate('plugins', {trigger: true});
        }
    },

    initialize: function (settings) {
        this.pluginName = settings.pluginName;
    },

    render: function () {
        this.$el.html(girder.templates.pluginConfigBreadcrumb({
            pluginName: this.pluginName
        }));

        return this;
    }
});
