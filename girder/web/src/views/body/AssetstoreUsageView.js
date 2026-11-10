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

// Okabe-Ito colors, which are distinguishable with common forms of color
// blindness, each with a label color that contrasts with it.  Every tile is
// also labeled, so color is never needed to tell tiles apart.
const TREEMAP_COLORS = [
    { background: '#0072B2', text: '#fff' },
    { background: '#E69F00', text: '#000' },
    { background: '#009E73', text: '#fff' },
    { background: '#F0E442', text: '#000' },
    { background: '#D55E00', text: '#fff' },
    { background: '#56B4E9', text: '#000' }
];
// The tile for children past the limit
const TREEMAP_MORE_COLOR = { background: '#666', text: '#fff' };

// Singular and plural names of resources for summarizing children past the
// limit.
const RESOURCE_NOUNS = {
    user: ['user', 'users'],
    collection: ['collection', 'collections'],
    folder: ['folder', 'folders'],
    item: ['item', 'items'],
    file: ['file', 'files']
};

/**
 * Describe the children that are past the limit, such as "29,900 more
 * items".  Item is only used for Girder items; children of mixed types are
 * called resources.
 *
 * @param other The summary of the children past the limit.
 */
function moreLabel(other) {
    const types = Object.keys(other.types || {});
    const plural = other.nodes === 1 ? 0 : 1;
    const nouns = types.length === 1 ? RESOURCE_NOUNS[types[0]] : null;
    const noun = nouns ? nouns[plural] : ['resource', 'resources'][plural];
    const count = String(other.nodes).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${count} more ${noun}`;
}

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
            resourceLink: (node) => this._resourceLink(node),
            moreLabel,
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

    /**
     * Get a link to the page of a resource.  A file links to its item, and
     * attached files link to the resource they are attached to.
     *
     * @param node An entry of the list of children.
     * @returns An object with the `href` and `title` of the link, or null if
     *     the entry has no page.
     */
    _resourceLink: function (node) {
        const parent = this.params.type ? `#${this.params.type}/${this.params.id}` : null;
        if (node.type === 'file') {
            return this.params.type === 'item'
                ? { href: parent, title: 'Open the item of this file' }
                : null;
        }
        if (node.type === 'attached') {
            return parent ? {
                href: parent,
                title: `Open the ${this.params.type} these files are attached to`
            } : null;
        }
        if (!RESOURCE_NOUNS[node.type] || !node._id) {
            return null;
        }
        return { href: `#${node.type}/${node._id}`, title: `Open this ${node.type}` };
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
        if (this.usage.other.size > 0) {
            nodes.push({ name: moreLabel(this.usage.other), size: this.usage.other.size, more: true });
            nodes.sort((a, b) => b.size - a.size);
        }
        const el = this.$('.g-usage-treemap')[0];
        if (!nodes.length || !el) {
            return;
        }
        let colorIndex = 0;
        const colors = nodes.map((node) => node.more
            ? TREEMAP_MORE_COLOR
            : TREEMAP_COLORS[colorIndex++ % TREEMAP_COLORS.length]);
        this.plot = new ApexCharts(el, {
            series: [{
                data: nodes.map((child) => ({ x: child.name || '(unnamed)', y: child.size }))
            }],
            colors: colors.map((color) => color.background),
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
                distributed: true,
                style: { colors: colors.map((color) => color.text) },
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
