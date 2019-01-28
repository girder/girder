import $ from 'jquery';
import _ from 'underscore';

import AssetstoreCollection from '@girder/core/collections/AssetstoreCollection';
import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import EditAssetstoreWidget from '@girder/core/views/widgets/EditAssetstoreWidget';
import NewAssetstoreWidget from '@girder/core/views/widgets/NewAssetstoreWidget';
import View from '@girder/core/views/View';
import { AssetstoreType } from '@girder/core/constants';
import { cancelRestRequests } from '@girder/core/rest';
import { confirm } from '@girder/core/dialog';
import events from '@girder/core/events';
import { formatSize } from '@girder/core/misc';
import { getCurrentUser } from '@girder/core/auth';

import AssetstoresTemplate from '@girder/core/templates/body/assetstores.pug';

import '@girder/core/stylesheets/body/assetstores.styl';

import 'as-jqplot/dist/jquery.jqplot.js';
import 'as-jqplot/dist/jquery.jqplot.css'; // jquery.jqplot.min.css
import 'as-jqplot/dist/plugins/jqplot.pieRenderer.js';

/**
 * This private data structure is a dynamic way to map assetstore types to the views
 * that should be rendered to import data into them.
 */
import FilesystemImportView from '@girder/core/views/body/FilesystemImportView';
import S3ImportView from '@girder/core/views/body/S3ImportView';
var assetstoreImportViewMap = {};
assetstoreImportViewMap[AssetstoreType.FILESYSTEM] = FilesystemImportView;
assetstoreImportViewMap[AssetstoreType.S3] = S3ImportView;

/**
 * This view shows the admin console, which links to all available admin pages.
 */
var AssetstoresView = View.extend({
    events: {
        'click .g-set-current': 'setCurrentAssetstore',
        'click .g-delete-assetstore': 'deleteAssetstore',
        'click .g-edit-assetstore': 'editAssetstore'
    },

    initialize: function (settings) {
        cancelRestRequests('fetch');
        this.plots = [];
        this.assetstoreEdit = settings.assetstoreEdit || false;
        this.importableTypes = [
            AssetstoreType.FILESYSTEM,
            AssetstoreType.S3
        ].concat(settings.importableTypes || []);

        this.newAssetstoreWidget = new NewAssetstoreWidget({
            parentView: this
        }).on('g:created', this.addAssetstore, this);

        // Fetch all of the current assetstores
        this.collection = new AssetstoreCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    destroy: function () {
        this._destroyPlots();
        View.prototype.destroy.call(this);
    },

    _destroyPlots: function () {
        for (let plot of this.plots) {
            plot.data('jqplot').destroy();
        }
        this.plots = [];
    },

    render: function () {
        if (!getCurrentUser() || !getCurrentUser().get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this._destroyPlots();
        this.$el.html(AssetstoresTemplate({
            assetstores: this.collection.toArray(),
            types: AssetstoreType,
            importableTypes: this.importableTypes,
            getAssetstoreImportRoute: this.getAssetstoreImportRoute
        }));

        this.newAssetstoreWidget.setElement(this.$('#g-new-assetstore-container')).render();

        _.each(this.$('.g-assetstore-capacity-chart'),
            this.capacityChart, this);

        if (this.assetstoreEdit) {
            this.editAssetstoreDialog(this.assetstoreEdit);
            this.assetstoreEdit = false;
        }

        return this;
    },

    addAssetstore: function (assetstore) {
        this.collection.add(assetstore);
        this.render();
    },

    /**
     * Renders the capacities of the assetstores in a pie chart using Chart.js.
     * @param el The canvas element to render in.
     */
    capacityChart: function (el) {
        var assetstore = this.collection.get($(el).attr('cid'));
        var capacity = assetstore.get('capacity');
        var used = capacity.total - capacity.free;
        var data = [
            ['Used (' + formatSize(used) + ')', used],
            ['Free (' + formatSize(capacity.free) + ')', capacity.free]
        ];
        var plot = $(el).jqplot([data], {
            seriesDefaults: {
                renderer: $.jqplot.PieRenderer,
                rendererOptions: {
                    sliceMargin: 2,
                    shadow: false,
                    highlightMouseOver: false,
                    showDataLabels: true,
                    padding: 5,
                    startAngle: 180
                }
            },
            legend: {
                show: true,
                location: 'e',
                background: 'transparent',
                border: 'none'
            },
            grid: {
                background: 'transparent',
                border: 'none',
                borderWidth: 0,
                shadow: false
            },
            gridPadding: {top: 10, right: 10, bottom: 10, left: 10}
        });
        this.plots.push(plot);
    },

    setCurrentAssetstore: function (evt) {
        var el = $(evt.currentTarget);
        var assetstore = this.collection.get(el.attr('cid'));
        assetstore.set({current: true});
        assetstore.off('g:saved').on('g:saved', function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Changed current assetstore.',
                type: 'success',
                timeout: 4000
            });
            this.collection.fetch({}, true);
        }, this).off('g:error').on('g:error', function (err) {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: err.responseJSON.message,
                type: 'danger'
            });
        }).save();
    },

    deleteAssetstore: function (evt) {
        var el = $(evt.currentTarget);
        var assetstore = this.collection.get(el.attr('cid'));

        confirm({
            text: 'Are you sure you want to delete the assetstore <b>' +
                  assetstore.escape('name') + '</b>?  There are no files ' +
                  'stored in it, and no data will be lost.',
            escapedHtml: true,
            yesText: 'Delete',
            confirmCallback: () => {
                assetstore.on('g:deleted', function () {
                    events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'Assetstore deleted.',
                        type: 'success',
                        timeout: 4000
                    });
                    this.collection.fetch({}, true);
                }, this).off('g:error').on('g:error', function (resp) {
                    events.trigger('g:alert', {
                        icon: 'attention',
                        text: resp.responseJSON.message,
                        type: 'danger',
                        timeout: 4000
                    });
                }, this).destroy();
            }
        });
    },

    editAssetstore: function (evt) {
        var cid = $(evt.currentTarget).attr('cid');
        this.editAssetstoreDialog(cid);
    },

    editAssetstoreDialog: function (cid) {
        var assetstore = this.collection.get(cid);
        var container = $('#g-dialog-container');

        var editAssetstoreWidget = new EditAssetstoreWidget({
            el: container,
            model: assetstore,
            parentView: this
        }).off('g:saved').on('g:saved', function () {
            this.render();
        }, this);
        editAssetstoreWidget.render();
    }
}, {
    import: function (assetstoreId) {
        var assetstore = new AssetstoreModel({ _id: assetstoreId });
        assetstore.once('g:fetched', function () {
            var View = assetstoreImportViewMap[assetstore.get('type')];
            if (View) {
                events.trigger('g:navigateTo', View, {
                    assetstore: assetstore
                });
            } else {
                throw new Error('No such view');
            }
        }).fetch();
    }
});

export default AssetstoresView;
