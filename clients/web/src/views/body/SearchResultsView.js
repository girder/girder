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
        this._query = settings.query;
        this._mode = settings.mode;
        // Give the display order of each type on the result view
        this._types = settings.types || ['collection', 'folder', 'item', 'group', 'user'];
        this._subviews = {};
        this._initResults = {};

        this._sizeOneElement = 28;
        this.pageLimit = 10;

        restRequest({
            url: 'resource/search',
            data: {
                q: this._query,
                mode: this._mode,
                types: JSON.stringify(_.intersection(
                    this._types,
                    SearchFieldWidget.getModeTypes(this._mode))
                ),
                limit: this.pageLimit
            }
        }).done(_.bind(function (results) {
            this._initResults = results;
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
        const icons = {
            'user': 'user',
            'group': 'users',
            'collection': 'sitemap',
            'folder': 'folder',
            'item': 'doc-text-inv'
        };
        return icons[type];
    },

    render: function () {
        this.$el.html(SearchResultsTemplate({
            query: this._query || null,
            length: this._calculateLength(this._initResults) || 0
        }));

        _.each(this._types, (type) => {
            if (this._initResults[type].length) {
                this._subviews[type] = new SearchResultsTypeView({
                    parentView: this,
                    name: `${type}ResultsView` || null,
                    type: type || '',
                    icon: this._getIcon(type) || '',
                    limit: this.pageLimit || 0,
                    query: this._query || null,
                    mode: this._mode || null,
                    initResults: this._initResults[type] || [],
                    sizeOneElement: this._sizeOneElement
                });
                this._subviews[type].render();
                this._subviews[type].$el.appendTo(this.$('.g-search-results-container'));
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

    className: 'g-search-results-type-container',

    initialize: function (settings) {
        this._name = settings.name;
        this._icon = settings.icon || '';
        this._type = settings.type || null;
        this._initResults = settings.initResults || null;
        this._pageLimit = settings.limit;
        this._query = settings.query;
        this._mode = settings.mode;
        this._sizeOneElement = settings.sizeOneElement || 35;

        this._paginateWidget = new SearchPaginateWidget({
            parentView: this,
            type: this._type,
            query: this._query,
            mode: this._mode,
            limit: this._pageLimit
        }).on('g:changed', function () {
            this._results = this._paginateWidget.results;
            this.render();
        }, this);

        this._results = this._initResults;
    },

    render: function () {
        this.$el.html(SearchResultsTypeTemplate({
            results: this._results,
            type: this._type,
            icon: this._icon
        }));

        this.$('.g-search-results-type').css('min-height', `${this._initResults.length * this._sizeOneElement}px`);
        this._paginateWidget.setElement(this.$(`#${this._type}Paginate`)).render();

        return this;
    }
});

export default SearchResultsView;
