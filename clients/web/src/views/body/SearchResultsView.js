import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';
import router from 'girder/router';

import SearchResultsTemplate from 'girder/templates/body/searchResults.pug';
import SearchResultsTypeTemplate from 'girder/templates/body/searchResultsType.pug';
import SearchPaginateWidget from 'girder/views/widgets/SearchPaginateWidget';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';

import 'girder/stylesheets/body/searchResultsList.styl';

/**
 * This view display all the search results by instanciating a subview
 * per each type found.
 */
var SearchResultsView = View.extend({
    events: {
        'click .g-search-result>a': function (e) {
            this._resultClicked($(e.currentTarget));
        }
    },

    initialize: function (settings) {
        this.query = settings.query;
        this.mode = settings.mode;
        // Give the display order of each type on the result view
        this.types = settings.types || ['collection', 'folder', 'item', 'group', 'user'];

        this.subviews = {};
        this.initResults = {};
        this.pageLimit = 3;

        const promises = [];
        let promiseTmp = null;

        _.each(this.types, (type) => {
            promiseTmp = restRequest({
                url: 'resource/search',
                data: {
                    q: this.query,
                    mode: this.mode,
                    types: JSON.stringify(_.intersection(
                        [type],
                        SearchFieldWidget.getModeTypes(this.mode))
                    ),
                    limit: this.pageLimit
                }
            }).done(_.bind(function (results) {
                this.initResults[type] = this._parseResults(results);
            }, this));
            promises.push(promiseTmp);
        });

        Promise.all(promises).then(_.bind(function () {
            this.render();
        }, this));
    },

    _calculateLength: function (results) {
        let length = 0;
        for (let type in results) {
            length += results[type].length;
        }
        return length;
    },

    _parseResults: function (results) {
        return Object.values(results)[0];
    },

    _getIcon: function (type) {
        let icon;
        if (type === 'user') {
            icon = 'user';
        } else if (type === 'group') {
            icon = 'users';
        } else if (type === 'collection') {
            icon = 'sitemap';
        } else if (type === 'folder') {
            icon = 'folder';
        } else if (type === 'item') {
            icon = 'doc-text-inv';
        }
        return icon;
    },

    render: function () {
        this.$el.html(SearchResultsTemplate({
            results: this.initResults || null,
            query: this.query || null,
            types: _.intersection(this.types, Object.keys(this.initResults)) || [],
            length: this._calculateLength(this.initResults) || 0
        }));

        _.each(this.types, (type) => {
            if (this.initResults[type].length) {
                this.subviews[type] = new SearchResultsTypeView({
                    parentView: this,
                    name: `${type}ResultsView` || null,
                    type: type || '',
                    icon: this._getIcon(type) || '',
                    limit: this.pageLimit || 0,
                    query: this.query || null,
                    mode: this.mode || null,
                    initResults: this.initResults[type] || []
                });
                this.subviews[type].setElement(this.$(`#${type}Subview`));
                this.subviews[type].render();
            }
        });

        return this;
    },

    _resultClicked: function (result) {
        router.navigate(result.attr('resourcetype') + '/' + result.attr('resourceid'), {
            trigger: true
        });
    }
});

/**
 * This subview display all the search results for one type.
 * It also contain a pagination widget that provide a consistent widget
 * for iterating amongst pages of a list of search results.
 */
var SearchResultsTypeView = View.extend({

    initialize: function (settings) {
        this.name = settings.name;
        this.icon = settings.icon;
        this.type = settings.type;
        this.results = settings.initResults;
        this.pageLimit = settings.limit;
        this.query = settings.query;
        this.mode = settings.mode;

        this.paginateWidget = new SearchPaginateWidget({
            parentView: this,
            type: this.type,
            query: this.query,
            mode: this.mode,
            limit: this.pageLimit
        }).on('g:changed', function () {
            this.results = this.paginateWidget.results;
            this.render();
        }, this);
    },

    render: function () {
        this.$el.html(SearchResultsTypeTemplate({
            results: this.results || null,
            type: this.type || null,
            icon: this.icon || ''
        }));

        this.paginateWidget.setElement(this.$(`#${this.type}Paginate`)).render();

        return this;
    }
});

export default SearchResultsView;
