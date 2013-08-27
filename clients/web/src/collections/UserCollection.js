girder.collections.UserCollection = Backbone.Collection.extend({
    model: girder.models.UserModel,

    offset: 0,
    sort: 'lastName',
    sortDir: girder.SORT_ASC,

    PAGE_LIMIT: 50,

    fetch: function (params) {
        "use strict";
        girder.restRequest({
            path: 'user',
            data: _.extend({
                'limit': this.PAGE_LIMIT,
                'offset': this.offset,
                'sort': this.sort,
                'sortdir': this.sortDir
            }, params || {})
        }).done(_.bind(function (users) {
            this.add(users);
            this.trigger('g:changed');
        }, this));
    }
});
