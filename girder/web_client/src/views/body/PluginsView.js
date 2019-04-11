import $ from 'jquery';
import _ from 'underscore';
// Bootstrap tooltip is required by popover
import 'bootstrap/js/tooltip';
import 'bootstrap/js/popover';

import router from '@girder/core/router';
import View from '@girder/core/views/View';
import { getPluginConfigRoute } from '@girder/core/utilities/PluginUtils';
import { restRequest, cancelRestRequests } from '@girder/core/rest';

import PluginFailedNoticeTemplate from '@girder/core/templates/widgets/pluginFailedNotice.pug';
import PluginsTemplate from '@girder/core/templates/body/plugins.pug';

import '@girder/core/stylesheets/body/plugins.styl';

/**
 * This is the plugin management page for administrators.
 */
var PluginsView = View.extend({
    events: {
        'click a.g-plugin-config-link': function (evt) {
            var route = $(evt.currentTarget).attr('g-route');
            router.navigate(route, { trigger: true });
        }
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        if (settings.all) {
            this.allPlugins = settings.all;
            this.failed = _.has(settings, 'failed') ? settings.failed : null;
            this.render();
        } else {
            // Fetch the plugin list
            restRequest({
                url: 'system/plugins',
                method: 'GET'
            })
                .done((resp) => {
                    this.allPlugins = resp.all;
                    this.failed = resp.failed;
                    this.render();
                }).fail(() => {
                    router.navigate('/', { trigger: true });
                });
        }
    },

    render: function () {
        _.each(this.allPlugins, function (info, name) {
            info.configRoute = getPluginConfigRoute(name);

            if (this.failed && _.has(this.failed, name)) {
                info.failed = this.failed[name];
            }
        }, this);

        this.$el.html(PluginsTemplate({
            allPlugins: this._sortPlugins(this.allPlugins)
        }));

        this.$('.g-plugin-list-item-failed-notice').popover({
            container: this.$el,
            template: PluginFailedNoticeTemplate()
        });
        this.$('.g-plugin-list-item-failed-notice').each(function () {
            $(this).attr('title', $(this).attr('native-title'));
        });

        return this;
    },

    _sortPlugins: function (plugins) {
        /* Sort a dictionary of plugins alphabetically so that the appear in a
         * predictable order to the user.
         *
         * @param plugins: a dictionary to sort.  Each entry has a .name
         *                 attribute used for sorting.
         * @returns sortedPlugins: the sorted list. */
        var sortedPlugins = _.map(plugins, function (value, key) {
            return { key: key, value: value };
        });
        sortedPlugins.sort(function (a, b) {
            return a.value.name.localeCompare(b.value.name);
        });
        return sortedPlugins;
    }
});

export default PluginsView;
