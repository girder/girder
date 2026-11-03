import $ from 'jquery';

import AssetstoreCollection from '@girder/core/collections/AssetstoreCollection';
import router from '@girder/core/router';
import View from '@girder/core/views/View';
import { cancelRestRequests, restRequest } from '@girder/core/rest';
import { getCurrentUser } from '@girder/core/auth';
import { DATE_SECOND, formatCount, formatDate, formatSize } from '@girder/core/misc';

import AssetstoreUsageTemplate from '@girder/core/templates/body/assetstoreUsage.pug';

import '@girder/core/stylesheets/body/assetstoreUsage.styl';

import ApexCharts from 'apexcharts';

const SOURCES = {
    all: 'All files',
    uploaded: 'Uploaded only',
    imported: 'Imported only'
};

const TYPE_NAMES = {
    user: 'User',
    collection: 'Collection',
    folder: 'Folder',
    item: 'Item',
    file: 'File',
    attached: 'Attached files',
    orphaned: 'Orphaned files',
    otherAttached: 'Attached files'
};

/**
 * This view shows how much storage users, collections, folders, items, and
 * files use, either in one assetstore or in all of them.  Clicking a user,
 * collection, folder, or item shows its contents.
 */
var AssetstoreUsageView = View.extend({
    events: {
        'change #g-usage-assetstore, #g-usage-source, #g-usage-attached, #g-usage-dedup': '_changeOptions',
        'click .g-usage-refresh': function () {
            this._fetch(true);
        },
        'submit .g-usage-controls': function (evt) {
            evt.preventDefault();
        }
    },

    /**
     * @param settings.assetstore The id of the assetstore to report on, or
     *     falsy for all assetstores.
     * @param settings.type The type of the resource whose contents are shown,
     *     or falsy to show users and collections.
     * @param settings.id The id of that resource.
     * @param settings.attached 'false' to exclude attached files.
     * @param settings.dedup 'true' to count shared stored data once.
     * @param settings.source 'all', 'uploaded', or 'imported'.
     */
    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.params = {
            assetstore: settings.assetstore || '',
            type: settings.type || '',
            id: settings.id || '',
            attached: settings.attached !== 'false' && settings.attached !== false,
            dedup: settings.dedup === 'true' || settings.dedup === true,
            source: SOURCES[settings.source] ? settings.source : 'all'
        };
        this.usage = null;
        this.error = null;
        this.plot = null;
        if (!getCurrentUser() || !getCurrentUser().get('admin')) {
            this.render();
            return;
        }
        this.assetstores = new AssetstoreCollection();
        this.assetstores.on('g:changed', this.render, this).fetch();
        this._fetch(false);
    },

    destroy: function () {
        this._destroyPlot();
        if (this._request) {
            this._request.abort();
        }
        View.prototype.destroy.call(this);
    },

    render: function () {
        if (!getCurrentUser() || !getCurrentUser().get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return this;
        }
        this._destroyPlot();
        this.$el.html(AssetstoreUsageTemplate({
            params: this.params,
            assetstores: this.assetstores ? this.assetstores.toArray() : [],
            sources: SOURCES,
            typeNames: TYPE_NAMES,
            usage: this.usage,
            error: this.error,
            link: (node) => '#' + this._route(node),
            formatSize,
            formatCount,
            formatDate,
            DATE_SECOND
        }));
        if (this.usage && this.usage.children.length) {
            this._renderTreemap();
        }
        return this;
    },

    /**
     * Get the route that shows a node with the current options.
     *
     * @param node An object with `type` and `_id`, or null for the list of
     *     users and collections.
     * @param params Options to use instead of the current ones.
     */
    _route: function (node, params) {
        params = params || this.params;
        const query = {};
        if (params.assetstore) {
            query.assetstore = params.assetstore;
        }
        if (node && node.type) {
            query.type = node.type;
            query.id = node._id;
        }
        if (!params.attached) {
            query.attached = 'false';
        }
        if (params.dedup) {
            query.dedup = 'true';
        }
        if (params.source !== 'all') {
            query.source = params.source;
        }
        const queryString = $.param(query);
        return 'assetstores/usage' + (queryString ? '?' + queryString : '');
    },

    _fetch: function (refresh) {
        if (this._request) {
            this._request.abort();
        }
        this.usage = null;
        this.error = null;
        this.render();
        const data = {
            attached: this.params.attached,
            dedup: this.params.dedup,
            source: this.params.source,
            limit: 100,
            topFiles: 20
        };
        if (this.params.assetstore) {
            data.assetstoreId = this.params.assetstore;
        }
        if (this.params.type) {
            data.parentType = this.params.type;
            data.parentId = this.params.id;
        }
        if (refresh) {
            data.refresh = true;
        }
        this._request = restRequest({
            url: 'assetstore/usage',
            data: data,
            error: null
        }).done((resp) => {
            this._request = null;
            this.usage = resp;
            this.render();
        }).fail((err) => {
            this._request = null;
            if (err.statusText === 'abort') {
                return;
            }
            this.error = (err.responseJSON && err.responseJSON.message) ||
                'Could not compute storage usage.';
            this.render();
        });
    },

    _changeOptions: function () {
        const params = {
            assetstore: this.$('#g-usage-assetstore').val(),
            attached: this.$('#g-usage-attached').is(':checked'),
            dedup: this.$('#g-usage-dedup').is(':checked'),
            source: this.$('#g-usage-source').val()
        };
        const node = this.params.type ? { type: this.params.type, _id: this.params.id } : null;
        router.navigate(this._route(node, params), { trigger: true });
    },

    _renderTreemap: function () {
        const nodes = this.usage.children.filter((child) => child.size > 0);
        const el = this.$('.g-usage-treemap')[0];
        if (!nodes.length || !el) {
            return;
        }
        this.plot = new ApexCharts(el, {
            series: [{
                data: nodes.map((child) => ({ x: child.name || '(unnamed)', y: child.size }))
            }],
            chart: {
                type: 'treemap',
                height: 420,
                animations: { enabled: false },
                toolbar: { show: false },
                events: {
                    dataPointSelection: (evt, chart, opts) => {
                        const node = nodes[opts.dataPointIndex];
                        if (node && node.drillable) {
                            router.navigate(this._route(node), { trigger: true });
                        }
                    }
                }
            },
            plotOptions: {
                treemap: {
                    distributed: true,
                    enableShades: false
                }
            },
            dataLabels: {
                enabled: true,
                formatter: (text, opts) => [text, formatSize(opts.value)]
            },
            tooltip: {
                y: { formatter: (value) => formatSize(value) }
            },
            legend: { show: false }
        });
        this.plot.render();
    },

    _destroyPlot: function () {
        if (this.plot) {
            this.plot.destroy();
            this.plot = null;
        }
    }
});

export default AssetstoreUsageView;
