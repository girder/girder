import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import PaginateWidgetTemplate from 'girder/templates/widgets/paginateWidget.pug';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget'
/**
 * This widget is used to provide a consistent widget for iterating amongst
 * pages of a list of element.
 */

 var SearchPaginateWidget = View.extend({
    events: {
        'click .g-page-next:not(.disabled)': function (e) {
            this.fetchNextPage(true);
        },
        'click .g-page-prev:not(.disabled)': function (e) {
            this.fetchPreviousPage(true);
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

        this.fetch().done(_.bind(function (results) {
            var result = results[this.type];
            this.results = result;
            this.trigger(`g:changed_${this.type}`);
            //this.render();
        },  this));
    },

    render: function () {
        this.$el.html(PaginateWidgetTemplate({
            collection: this
        }));

        this.$('.g-page-next').girderEnable(this.hasNextPage());
        this.$('.g-page-prev').girderEnable(this.hasPreviousPage());
        return this;
    },

    pageNum: function () {
        return this._currentPage;
    },

    hasPreviousPage: function () {
        // TODO: Something is missing NEVER do that
        if (this._currentPage) {
            var done = false
            this.fetchPreviousPage().done(_.bind(function () {
                done = true;
            }));
            while (!done) {

            };
        }
        return this._hasPreviousPage;
    },

    hasNextPage: function () {
        // TODO: Something is missing
        var done = false
        this.fetchNextPage().done(_.bind(function () {
            done = true;
        }));
        while (!done) {
        console.log(done);

        };
        return this._hasNextPage;
    },

    fetchPreviousPage: function (update = false) {
        var offset = this.limit * (this._currentPage - 1);
        if (offset < 0) {
            this._hasPreviousPage = false;
        } else {
            return this.fetch(offset).done(_.bind(function (results) {
                var result = results[this.type];
                console.log('PREV: ', result);
                if (result.length > 0) {
                    this._hasPreviousPage = true;
                    if (update) {
                        this.results = result;
                        this.trigger(`g:changed_${this.type}`);
                        this._currentPage--;
                    }
                } else {
                    this._hasPreviousPage = false;
                }
                //console.log('PREV: ', this._hasPreviousPage);
            }, this));
        }
    },

    fetchNextPage: function (update = false) {
        var offset = this.limit * (this._currentPage + 1);
        return this.fetch(offset).done(_.bind(function (results) {
            var result = results[this.type];
            //console.log('NEXT: ', result);
            if (result.length > 0) {
                this._hasNextPage = true;
                if (update) {
                    this.results = result;
                    this.trigger(`g:changed_${this.type}`);
                    this._currentPage++;
                }
            } else {
                this._hasNextPage = false;
            }
            console.log('NEXT: ', this._hasNextPage);
        }, this));
    },

    fetch: function (offset) {
        return restRequest({
            url: 'resource/search',
            data: {
                q: this.query,
                mode: this.mode,
                types: JSON.stringify(_.intersection(
                    this.type,
                    SearchFieldWidget.getModeTypes(this.mode))
                ),
                limit: this.limit,
                offset: offset
            }
        });
    }
});

export default SearchPaginateWidget;
