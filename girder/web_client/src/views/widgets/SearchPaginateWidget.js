import _ from 'underscore';

import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';

import PaginateWidgetTemplate from '@girder/core/templates/widgets/paginateWidget.pug';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';
/**
 * This widget is used to provide a consistent widget for iterating amongst
 * pages of a list of search results (using a search mode, a query, an unique type,
 * and a limit).
 */

var SearchPaginateWidget = View.extend({
    events: {
        'click .g-page-next:not(.disabled)': function (e) {
            this._updateHasNextPage(true);
        },
        'click .g-page-prev:not(.disabled)': function (e) {
            this._updateHasPreviousPage(true);
        }
    },

    initialize: function (settings) {
        this._type = settings.type;
        this._query = settings.query;
        this._mode = settings.mode;
        this._limit = settings.limit;

        this._offset = 0;
        this._currentPage = 0;
        this._hasNextPage = false;
        this._hasPreviousPage = false;

        this.results = null;

        this._updateHasNextPage();
    },

    render: function () {
        this.$el.html(PaginateWidgetTemplate({
            collection: this
        }));

        this.$('.g-page-next').girderEnable(this._hasNextPage);
        this.$('.g-page-prev').girderEnable(this._hasPreviousPage);

        if (!this._hasNextPage && !this._hasPreviousPage) {
            this.$el.hide();
        } else {
            this.$el.show();
        }

        return this;
    },

    pageNum: function () {
        return this._currentPage;
    },

    _updateHasPreviousPage: function (update = false) {
        if (this._currentPage) {
            if (update) {
                return this._fetchPreviousPage(update)
                    .done(() => {
                        return this._fetchPreviousPage();
                    });
            } else {
                return this._fetchPreviousPage();
            }
        } else {
            return this._fetchPreviousPage();
        }
    },

    _updateHasNextPage: function (update = false) {
        if (update) {
            return this._fetchNextPage(update)
                .done(() => {
                    return this._fetchNextPage();
                });
        } else {
            return this._fetchNextPage();
        }
    },

    _fetchPreviousPage: function (update = false) {
        var offset = this._limit * (this._currentPage - 1);
        if (offset < 0) {
            this._hasPreviousPage = false;
            this.render();
        } else {
            return this._fetch(offset)
                .done((results) => {
                    var result = results[this._type];
                    if (result.length) {
                        this._hasPreviousPage = true;
                        if (update) {
                            this.results = result;
                            this.trigger('g:changed');
                            this._currentPage--;
                            this._updateHasNextPage();
                        }
                    } else {
                        this._hasPreviousPage = false;
                    }
                    this.render();
                });
        }
    },

    _fetchNextPage: function (update = false) {
        var offset = this._limit * (this._currentPage + 1);
        return this._fetch(offset)
            .done((results) => {
                var result = results[this._type];
                if (result.length) {
                    this._hasNextPage = true;
                    if (update) {
                        this.results = result;
                        this.trigger('g:changed');
                        this._currentPage++;
                        this._updateHasPreviousPage();
                    }
                } else {
                    this._hasNextPage = false;
                }
                this.render();
            });
    },

    _fetch: function (offset) {
        return restRequest({
            url: 'resource/search',
            data: {
                q: this._query,
                mode: this._mode,
                types: JSON.stringify(_.intersection(
                    [this._type],
                    SearchFieldWidget.getModeTypes(this._mode))
                ),
                limit: this._limit,
                offset: offset
            }
        });
    }
});

export default SearchPaginateWidget;
