girder.collections.CollectionCollection = Backbone.Collection.extend({
    model: girder.models.CollectionModel,

    sort: 'name',
    sortDir: girder.SORT_ASC,

    PAGE_LIMIT: 50,

    fetch: function (params) {
        girder.restRequest({
            path: 'collection',
            data: _.extend({
                'limit': this.PAGE_LIMIT,
                'offset': this.length,
                'sort': this.sort,
                'sortdir': this.sortDir
            }, params || {})
        }).done(_.bind(function (collections) {
            this.add(collections);
            this.trigger('g:changed');
        }, this));
    }
});