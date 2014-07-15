/**
 * This view shows the admin console, which links to all available admin pages.
 */
girder.views.AssetstoresView = girder.View.extend({
    events: {
        'click .g-set-current': 'setCurrentAssetstore',
        'click .g-delete-assetstore': 'deleteAssetstore'
    },

    initialize: function () {

        // Fetch all of the current assetstores
        if (girder.currentUser && girder.currentUser.get('admin')) {
            this.collection = new girder.collections.AssetstoreCollection();
            this.collection.on('g:changed', function () {
                this.render();
            }, this).fetch();
        }
        else {
            this.render();
        }
    },

    render: function () {
        if (!girder.currentUser || !girder.currentUser.get('admin')) {
            this.$el.text('Must be logged in as admin to view this page.');
            return;
        }
        this.$el.html(jade.templates.assetstores({
            assetstores: this.collection.models,
            types: girder.AssetstoreType
        }));
        this.newAssetstoreWidget = new girder.views.NewAssetstoreWidget({
            el: this.$('#g-new-assetstore-container')
        });
        this.newAssetstoreWidget
            .off().on('g:created', this.addAssetstore, this).render();

        _.each(this.$('.g-assetstore-capacity-chart'),
            this.capacityChart, this);

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
        var data = [
            ['Free', capacity.free],
            ['Used', capacity.total - capacity.free]
        ];
        var plot = $(el).jqplot([data], {
            seriesDefaults: {
                renderer: $.jqplot.PieRenderer,
                rendererOptions: {
                    sliceMargin: 2,
                    shadow: false,
                    highlightMouseOver: false
                }
            },
            legend: {
                show: true,
                location: 'e',
                border: 'none'
            },
            grid: {
                background: '#fff',
                borderColor: '#fff',
                shadow: false
            }
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
        }, this).save();
    },

    deleteAssetstore: function (evt) {
        var el = $(evt.currentTarget);
        var assetstore = this.collection.get(el.attr('cid'));

        girder.confirm({
            text: 'Are you sure you want to delete the assetstore <b>' +
                  assetstore.get('name') + '</b>?',
            yesText: 'Delete',
            confirmCallback: _.bind(function () {
                assetstore.on('g:deleted', function () {
                    girder.events.trigger('g:alert', {
                        icon: 'ok',
                        text: 'Assetstore deleted.',
                        type: 'success',
                        timeout: 4000
                    });

                    this.collection.remove(assetstore);
                    this.render();
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
    }
});

girder.router.route('assetstores', 'assetstores', function () {
    girder.events.trigger('g:navigateTo', girder.views.AssetstoresView);
});
