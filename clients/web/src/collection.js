/**
 * All collections should descend from this collection base class, which
 * provides nice utilities for pagination and sorting.
 */
girder.Collection = Backbone.Collection.extend({
    resourceName: null,

    sortField: 'name',
    sortDir: girder.SORT_ASC,

    // Number of records to fetch per page
    pageLimit: 50,
    offset: 0,

    /**
     * Append mode can be used to append pages to the collection rather than
     * simply replacing its contents when a new page is fetched. For the sake
     * of least surprise, this property should not be changed in the definition
     * of collections, but after they are instantiated.
     */
    append: false,

    /**
     * After you have called fetch() on a collection, this method will tell
     * you whether there are more pages remaining to be fetched, or if you
     * have hit the end.
     */
    hasMorePages: function () {
        return this._hasMorePages;
    },

    /**
     * Fetches the next page of this collection, replacing the existing models
     * of this collection with the requested page. If the next page contains
     * any records (i.e. it was not already on the last page), this will
     * trigger g:changed.
     */
    fetch: function (params) {
        if (this.resourceName === null) {
            alert('Error: You must set a resourceName on your collection.');
            return;
        }

        girder.restRequest({
            path: this.resourceName,
            data: _.extend({
                'limit': this.pageLimit + 1,
                'offset': this.offset,
                'sort': this.sortField,
                'sortdir': this.sortDir
            }, params || {})
        }).done(_.bind(function (list) {
            if (list.length > this.pageLimit) {
                // This means we have more pages to display still. Pop off
                // the extra that we fetched.
                list.pop();
                this._hasMorePages = true;
            }
            else {
                this._hasMorePages = false;
            }

            this.offset += list.length;

            if (list.length > 0) {
                if (this.append) {
                    this.add(list);
                }
                else {
                    this.reset(list);
                }
            }

            this.trigger('g:changed');
        }, this));
    }
});
