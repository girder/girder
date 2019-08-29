import _ from 'underscore';
import Backbone from 'backbone';

import { localeComparator } from '@girder/core/misc';
import Model from '@girder/core/models/Model';
import { restRequest } from '@girder/core/rest';
import { SORT_ASC } from '@girder/core/constants';

/**
 * All collections should descend from this collection base class, which
 * provides nice utilities for pagination and sorting.
 */
var Collection = Backbone.Collection.extend({
    model: Model,
    resourceName: null,

    sortField: 'name',
    sortDir: SORT_ASC,
    comparator: localeComparator,

    // Number of records to fetch per page
    pageLimit: 25,
    offset: 0,

    // Alternative fetch URL
    altUrl: null,

    /**
     * Append mode can be used to append pages to the collection rather than
     * simply replacing its contents when a new page is fetched. For the sake
     * of least surprise, this property should not be changed in the definition
     * of collections, but after they are instantiated.
     */
    append: false,

    /**
     * Client-side filtering: set to a function that takes an instance of this
     * collection's model and returns true for each instance that should be
     * included in this collection.  For the sake of least surprise, this
     * property should not be changed in the definition of collections, but
     * after they are instantiated.
     */
    filterFunc: null,

    /**
     * If filtering and not appending, this stack is used to record the offsets
     * at which prior pages had been fetched.
     */
    pageOffsetStack: null,

    /**
     * Returns a boolean of whether or not this collection has previous pages,
     * i.e. if the offset of the current page start is > 0
     */
    hasPreviousPage: function () {
        if (this.filterFunc) {
            if (this.append) { return false; }
            this.pageOffsetStack = this.pageOffsetStack || [];
            return (this.pageOffsetStack.length > 1);
        }
        return this.offset - this.length > 0;
    },

    /**
     * After you have called fetch() on a collection, this method will tell
     * you whether there are more pages remaining to be fetched, or if you
     * have hit the end.
     */
    hasNextPage: function () {
        return this._hasMorePages;
    },

    /**
     * Fetch the previous page of this collection, emitting g:changed when done.
     */
    fetchPreviousPage: function (params) {
        if (this.filterFunc) {
            if (this.append) {
                this.offset = 0;
            } else {
                this.pageOffsetStack = this.pageOffsetStack || [];
                if (this.pageOffsetStack.length) {
                    this.pageOffsetStack.pop();
                }

                this.offset = (
                    this.pageOffsetStack.length ? this.pageOffsetStack.pop() : 0
                );
            }
        } else {
            this.offset = Math.max(
                0,
                this.offset - this.length - this.pageLimit);
        }
        return this.fetch(_.extend({}, this.params, params || {}));
    },

    /**
     * Fetch the next page of this collection, emitting g:changed when done.
     */
    fetchNextPage: function (params) {
        return this.fetch(_.extend({}, this.params, params || {}));
    },

    /**
     * Return the 0-indexed page number of the current page. Add 1 to this
     * result when displaying it to the user.
     *
     * If this collection hasn't been fully initialized (i.e.: before any pages
     * have been fetched), pageNum() may return a page number < 0 to signal that
     * there is no "current page".
     */
    pageNum: function () {
        if (this.filterFunc) {
            if (this.append) { return 0; }
            this.pageOffsetStack = this.pageOffsetStack || [];
            return this.pageOffsetStack.length - 1;
        }
        return Math.ceil((this.offset - this.length) / this.pageLimit);
    },

    /**
     * Fetches the next page of this collection, replacing the existing models
     * of this collection with the requested page. If the next page contains
     * any records (i.e. it was not already on the last page), this will
     * trigger g:changed.
     * @param params Any additional parameters to be passed with the request.
     * @param reset Set this to true to re-fetch the current page.
     */
    fetch: function (params, reset) {
        if (this.altUrl === null && this.resourceName === null) {
            throw new Error('An altUrl or resourceName must be set on the Collection.');
        }

        if (this.filterFunc && !this.append) {
            this.pageOffsetStack = this.pageOffsetStack || [];
        }

        if (reset) {
            if (this.filterFunc && !this.append) {
                this.pageOffsetStack = [];
            }
            this.offset = 0;
        } else {
            this.params = params || {};
        }

        if (this.filterFunc && !this.append) {
            this.pageOffsetStack.push(this.offset);
        }

        var limit = this.pageLimit > 0 ? this.pageLimit + 1 : 0;

        var finalList = []; /* will be built up in pieces */

        function fetchListFragment() {
            var xhr = restRequest({
                url: this.altUrl || this.resourceName,
                data: _.extend({
                    limit: limit,
                    offset: this.offset,
                    sort: this.sortField,
                    sortdir: this.sortDir
                }, this.params)
            });

            var result = xhr.then((list) => {
                if (this.pageLimit > 0 && list.length > this.pageLimit) {
                    // This means we have more pages to display still. Pop off
                    // the extra that we fetched.
                    list.pop();
                    this._hasMorePages = true;
                } else {
                    this._hasMorePages = false;
                }

                var offsetDelta = list.length;

                /*
                 * If filtering, decorate the list with their pre-filtered
                 * indexes.  The index will be needed when adjusting the offset.
                 */
                if (this.filterFunc) {
                    var filter = this.filterFunc;
                    list = (
                        list
                            .map(function (x, index) { return [index, x]; })
                            .filter(function (tuple) {
                                return filter(tuple[1]);
                            })
                    );
                }

                var numUsed = list.length;
                var wantMorePages = (
                    (this.pageLimit === 0) ||
                    (finalList.length + numUsed < this.pageLimit)
                );

                /* page is complete */
                if (!wantMorePages && this.pageLimit > 0) {
                    /*
                     * If we fetched more data than we needed to complete the
                     * page, then newNumUsed will be < numUsed ...
                     */
                    var newNumUsed = this.pageLimit - finalList.length;
                    if (numUsed > newNumUsed) {
                        /*
                         * ...therefore, entries are being left out at the end,
                         * so they necessesarily remain to be fetched.
                         */
                        this._hasMorePages = true;
                        numUsed = newNumUsed;
                    }

                    /*
                     * correct the offset: it must be advanced beyond the
                     * last element that got used.
                     */
                    if (this.filterFunc) {
                        /*
                         * If filtering, consult the index for the last element
                         * to be featured on this page.
                         */
                        offsetDelta = list[numUsed - 1][0] + 1;
                    } else {
                        /*
                         * Otherwise, the first numUsed elements will be
                         * unconditionally featured.
                         */
                        offsetDelta = numUsed;
                    }
                }

                list = list.slice(0, numUsed);
                /* If filtering, undecorate the list. */
                if (this.filterFunc) {
                    list = list.map(function (tuple) { return tuple[1]; });
                }

                finalList = finalList.concat(list);
                this.offset += offsetDelta;

                if (wantMorePages && this._hasMorePages) {
                    return fetchListFragment.apply(this);
                } else {
                    if (finalList.length > 0 || reset) {
                        if (this.append && !reset) {
                            this.add(finalList);
                        } else {
                            this.reset(finalList);
                        }
                    }

                    this.trigger('g:changed');
                }
                return undefined;
            });
            xhr.girder = { fetch: true };
            return result;
        }

        return fetchListFragment.apply(this);
    }
});

export default Collection;
