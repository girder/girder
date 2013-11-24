/**
 * This view shows the admin console, which links to all available admin pages.
 */
girder.views.AssetstoresView = Backbone.View.extend({
    events: {

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
        // This page should be re-rendered if the user logs in or out
        girder.events.on('g:login', this.render, this);
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

        girder.router.navigate('assetstores');

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
    }
});

girder.router.route('assetstores', 'assetstores', function () {
    girder.events.trigger('g:navigateTo', girder.views.AssetstoresView);
});
