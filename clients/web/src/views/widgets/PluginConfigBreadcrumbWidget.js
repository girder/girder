var girder = require('girder/init');
var View   = require('girder/view');

var PluginConfigBreadcrumbTemplate = require('girder/templates/widgets/pluginConfigBreadcrumb.jade');

/**
 * This widget provides a consistent breadcrumb to be displayed on the admin
 * configuration pages for plugins.
 */
var PluginConfigBreadcrumbWidget = View.extend({
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
        this.$el.html(PluginConfigBreadcrumbTemplate({
            pluginName: this.pluginName
        }));

        return this;
    }
});

module.exports = PluginConfigBreadcrumbWidget;
