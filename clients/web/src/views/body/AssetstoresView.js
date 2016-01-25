/**
 * This view shows the admin console, which links to all available admin pages.
 */
girder.views.AssetstoresView = girder.View.extend({
    events: {
        'click .g-set-current': 'setCurrentAssetstore',
        'click .g-delete-assetstore': 'deleteAssetstore',
        'click .g-edit-assetstore': 'editAssetstore'
    },

    initialize: function (settings) {
        girder.cancelRestRequests('fetch');
        this.assetstoreEdit = settings.assetstoreEdit || false;
        this.importableTypes = [
            girder.AssetstoreType.FILESYSTEM,
            girder.AssetstoreType.S3
        ].concat(settings.importableTypes || []);

        this.newAssetstoreWidget = new girder.views.NewAssetstoreWidget({
            parentView: this
        }).on('g:created', this.addAssetstore, this);

        // Fetch all of the current assetstores
        this.collection = new girder.collections.AssetstoreCollection();
        this.collection.on('g:changed', function () {
            this.render();
        }, this).fetch();
    },

    render: function () {
        if (!girder.currentUser || !girder.currentUser.get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(girder.templates.assetstores({
            assetstores: this.collection.toArray(),
            types: girder.AssetstoreType,
            importableTypes: this.importableTypes,
            getAssetstoreImportRoute: this.getAssetstoreImportRoute
        }));

        this.newAssetstoreWidget.setElement(this.$('#g-new-assetstore-container')).render();
        this.$('.g-assetstore-button-container[title]').tooltip();

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
            ['Used (' + girder.formatSize(used) + ')', used],
            ['Free (' + girder.formatSize(capacity.free) + ')', capacity.free]
        ];
        $(el).jqplot([data], {
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
    },

    setCurrentAssetstore: function (evt) {
        var el = $(evt.currentTarget);
        var assetstore = this.collection.get(el.attr('cid'));
        assetstore.set({current: true});
        assetstore.off('g:saved').on('g:saved', function () {
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'Changed current assetstore.',
                type: 'success',
                timeout: 4000
            });
            this.collection.fetch({}, true);
        }, this).off('g:error').on('g:error', function (err) {
            girder.events.trigger('g:alert', {
                icon: 'cancel',
                text: err.responseJSON.message,
                type: 'danger'
            });
        }).save();
    },

    deleteAssetstore: function (evt) {
        var el = $(evt.currentTarget);
        var assetstore = this.collection.get(el.attr('cid'));

        girder.confirm({
            text: 'Are you sure you want to delete the assetstore <b>' +
                  assetstore.escape('name') + '</b>?  There are no files ' +
                  'stored in it, and no data will be lost.',
            escapedHtml: true,
            yesText: 'Delete',
            confirmCallback: _.bind(function () {
                assetstore.on('g:deleted', function () {
                    girder.events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'Assetstore deleted.',
                        type: 'success',
                        timeout: 4000
                    });
                    this.collection.fetch({}, true);
                }, this).off('g:error').on('g:error', function (resp) {
                    girder.events.trigger('g:alert', {
                        icon: 'attention',
                        text: resp.responseJSON.message,
                        type: 'danger',
                        timeout: 4000
                    });
                }, this).destroy();
            }, this)
        });
    },

    editAssetstore: function (evt) {
        var cid = $(evt.currentTarget).attr('cid');
        this.editAssetstoreDialog(cid);
    },

    editAssetstoreDialog: function (cid) {
        var assetstore = this.collection.get(cid);
        var container = $('#g-dialog-container');

        var editAssetstoreWidget = new girder.views.EditAssetstoreWidget({
            el: container,
            model: assetstore,
            parentView: this
        }).off('g:saved').on('g:saved', function () {
            this.render();
        }, this);
        editAssetstoreWidget.render();
    }
});

/**
 * This data structure is a dynamic way to map assetstore types to the views
 * that should be rendered to import data into them.
 */
girder.assetstoreImportViewMap = {};
girder.assetstoreImportViewMap[girder.AssetstoreType.FILESYSTEM] = 'FilesystemImportView';
girder.assetstoreImportViewMap[girder.AssetstoreType.S3] = 'S3ImportView';

girder.router.route('assetstores', 'assetstores', function (params) {
    girder.events.trigger('g:navigateTo', girder.views.AssetstoresView, {
        assetstoreEdit: params.dialog === 'assetstoreedit'
                        ? params.dialogid : false
    });
});

girder.router.route('assetstore/:id/import', 'assetstoreImport', function (assetstoreId) {
    var assetstore = new girder.models.AssetstoreModel({
        _id: assetstoreId
    });

    assetstore.once('g:fetched', function () {
        var viewName = girder.assetstoreImportViewMap[assetstore.get('type')],
            view = girder.views[viewName];

        if (!view) {
            throw 'No such view: ' + viewName;
        }
        girder.events.trigger('g:navigateTo', view, {
            assetstore: assetstore
        });
    }).fetch();
});
