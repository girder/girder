girder.views.geospatial_ItemWidget = girder.View.extend({
    initialize: function (settings) {
        this.accessLevel = settings.accessLevel;
        this.item = settings.item;
        this.item.on('g:changed', function () {
            this.render();
        }, this);
        this.render();
    },
    render: function () {
        this.$el.html(girder.templates.geospatial_item({
            accessLevel: this.accessLevel,
            girder: girder,
            item: this.item
        }));
        return this;
    }
});

girder.wrap(girder.models.ItemModel, 'fetch', function (fetch) {
    fetch.call(this);
    girder.restRequest({
        path: this.resourceName + '/' + this.get('_id') + '/geospatial',
        error: null
    }).done(_.bind(function (resp) {
        this.set(resp);
    }, this)).error(_.bind(function (err) {
        this.trigger('g:error', err);
    }, this));
    return this;
});

girder.wrap(girder.views.ItemView, 'render', function (render) {
    this.model.getAccessLevel(_.bind(function (accessLevel) {
        render.call(this);
        var element = $('<div class="g-item-geospatial"/>');
        $('.g-item-metadata').after(element);
        this.geospatialItemWidget = new girder.views.geospatial_ItemWidget({
            accessLevel: accessLevel,
            el: element,
            item: this.model,
            parentView: this
        });
    }, this));

    return this;
});
