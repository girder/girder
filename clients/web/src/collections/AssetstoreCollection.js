girder.collections.AssetstoreCollection = Backbone.Collection.extend({
    model: girder.models.AssetstoreModel,

    sort: 'name',
    sortDir: girder.SORT_ASC,

    PAGE_LIMIT: 50,

    fetch: function (params) {
        girder.restRequest({
            path: 'assetstore',
            data: _.extend({
                'limit': this.PAGE_LIMIT,
                'offset': this.length,
                'sort': this.sort,
                'sortdir': this.sortDir
            }, params || {})
        }).done(_.bind(function (assetstores) {
            this.add(assetstores);
            this.trigger('g:changed');
        }, this));
    }
});
