/* eslint-disable backbone/collection-model */
import PageableCollection from 'backbone.paginator';
import { apiRoot } from 'girder/rest';

const queryParams = {
    currentPage: null,
    order: null,
    pageSize: 'limit',
    sortKey: 'sort',
    offset() {
        return (this.state.currentPage - 1) * this.state.pageSize;
    },
    sortdir() {
        return -(this.state.order);
    }
};

export default PageableCollection.extend({
    initialize(models, options = {}) {
        this.parent = options.parent;
    },
    resource: null,
    mode: 'infinite',
    url() {
        return `${apiRoot}/${this.resource}`;
    },
    queryParams,

    setParent(parent) {
        this.parent = parent;
        return this;
    },

    /* work around bugs in infinite mode */
    reset() {
        this.links = {
            '1': this.url
        };
        return PageableCollection.prototype.reset.apply(this, arguments);
    },
    setPageSize() {
        this.reset();
        return PageableCollection.prototype.setPageSize(this, arguments);
    }
});
