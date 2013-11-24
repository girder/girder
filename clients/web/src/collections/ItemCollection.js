girder.collections.ItemCollection = Backbone.Collection.extend({
    model: girder.models.ItemModel,

    sortField: 'name',
    sortDir: girder.SORT_ASC,

    PAGE_LIMIT: 100,

    comparator: function (model1, model2) {
        var a1 = model1.get(this.sortField),
            a2 = model2.get(this.sortField);

        if (typeof(a1) === 'string') {
            a1 = a1.toLowerCase();
            a2 = a2.toLowerCase();
        }
        if (a1 > a2) {
            return this.sortDir;
        }
        else {
            return -this.sortDir;
        }
    },

    fetch: function (params) {
        girder.restRequest({
            path: 'item',
            data: _.extend({
                'limit': this.PAGE_LIMIT,
                'offset': this.length,
                'sort': this.sortField,
                'sortdir': this.sortDir
            }, params || {})
        }).done(_.bind(function (items) {
            this.add(items);
            this.trigger('g:changed');
        }, this));
    }
});
