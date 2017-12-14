import _ from 'underscore';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import PaginateWidgetTemplate from 'girder/templates/widgets/paginateWidget.pug';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';
/**
 * This widget is used to provide a consistent widget for iterating amongst
 * pages of a list of search results (using a search mode, a query, an unique type,
 * and a limit).
 */

var SearchPaginateWidget = View.extend({
    events: {
        'click .g-page-next:not(.disabled)': function (e) {
            this.updateHasNextPage(true);
        },
        'click .g-page-prev:not(.disabled)': function (e) {
            this.updateHasPreviousPage(true);
        }
    },

    initialize: function (settings) {
        this.type = settings.type;
        this.query = settings.query;
        this.mode = settings.mode;
        this.limit = settings.limit;

        this.offset = 0;
        this._currentPage = 0;
        this._hasNextPage = false;
        this._hasPreviousPage = false;

        this.updateHasNextPage();
    },

    render: function () {
        this.$el.html(PaginateWidgetTemplate({
            collection: this
        }));

        this.$('.g-page-next').girderEnable(this._hasNextPage);
        this.$('.g-page-prev').girderEnable(this._hasPreviousPage);
        return this;
    },

    pageNum: function () {
        return this._currentPage;
    },

    updateHasPreviousPage: function (update = false) {
        if (this._currentPage) {
            if (update) {
                return this.fetchPreviousPage(update).done(_.bind(function () {
                    return this.fetchPreviousPage();
                }, this));
            } else {
                return this.fetchPreviousPage();
            }
        } else {
            return this.fetchPreviousPage();
        }
    },

    updateHasNextPage: function (update = false) {
        if (update) {
            return this.fetchNextPage(update).done(_.bind(function () {
                return this.fetchNextPage();
            }, this));
        } else {
            return this.fetchNextPage();
        }
    },

    fetchPreviousPage: function (update = false) {
        var offset = this.limit * (this._currentPage - 1);
        if (offset < 0) {
            this._hasPreviousPage = false;
            this.render();
        } else {
            return this.fetch(offset).done(_.bind(function (results) {
                var result = results[this.type];
                if (result.length) {
                    this._hasPreviousPage = true;
                    if (update) {
                        this.results = result;
                        this.trigger('g:changed');
                        this._currentPage--;
                        this.updateHasNextPage();
                    }
                } else {
                    this._hasPreviousPage = false;
                }
                this.render();
            }, this));
        }
    },

    fetchNextPage: function (update = false) {
        var offset = this.limit * (this._currentPage + 1);
        return this.fetch(offset).done(_.bind(function (results) {
            var result = results[this.type];
            if (result.length) {
                this._hasNextPage = true;
                if (update) {
                    this.results = result;
                    this.trigger('g:changed');
                    this._currentPage++;
                    this.updateHasPreviousPage();
                }
            } else {
                this._hasNextPage = false;
            }
            this.render();
        }, this));
    },

    fetch: function (offset) {
        return restRequest({
            url: 'resource/search',
            data: {
                q: this.query,
                mode: this.mode,
                types: JSON.stringify(_.intersection(
                    [this.type],
                    SearchFieldWidget.getModeTypes(this.mode))
                ),
                limit: this.limit,
                offset: offset
            }
        });
    }
});

export default SearchPaginateWidget;
