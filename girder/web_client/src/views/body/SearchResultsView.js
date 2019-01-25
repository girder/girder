import _ from 'underscore';

import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import SearchPaginateWidget from '@girder/core/views/widgets/SearchPaginateWidget';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';

import SearchResultsTemplate from '@girder/core/templates/body/searchResults.pug';
import SearchResultsTypeTemplate from '@girder/core/templates/body/searchResultsType.pug';
import '@girder/core/stylesheets/body/searchResultsList.styl';

/**
 * This view display all the search results by instantiating a subview
 * per each type found.
 */
var SearchResultsView = View.extend({
    initialize: function (settings) {
        this._query = settings.query || '';
        this._mode = settings.mode || 'text';

        this._sizeOneElement = 28;
        this.pageLimit = 10;

        this._request = restRequest({
            url: 'resource/search',
            data: {
                q: this._query,
                mode: this._mode,
                types: JSON.stringify(SearchFieldWidget.getModeTypes(this._mode)),
                limit: this.pageLimit
            }
        });
        this.render();
    },

    /**
     * Return a consistent and semantically-meaningful type ordering.
     */
    _getTypeOrdering: function (resultTypes) {
        // This ordering places hopefully-more relevant types first
        const builtinOrdering = ['collection', 'folder', 'item', 'group', 'user'];

        // _.intersection will use the ordering of its first argument
        const orderedKnownTypes = _.intersection(builtinOrdering, resultTypes);
        const orderedUnknownTypes =  _.difference(resultTypes, builtinOrdering).sort();

        return orderedKnownTypes.concat(orderedUnknownTypes);
    },

    render: function () {
        this.$el.html(SearchResultsTemplate({
            query: this._query
        }));
        this._subviews = {};

        this._request
            .done((results) => {
                this.$('.g-search-pending').hide();

                const resultTypes =  _.keys(results);
                const orderedTypes = this._getTypeOrdering(resultTypes);
                _.each(orderedTypes, (type) => {
                    if (results[type].length) {
                        this._subviews[type] = new SearchResultsTypeView({
                            parentView: this,
                            query: this._query,
                            mode: this._mode,
                            type: type,
                            limit: this.pageLimit,
                            initResults: results[type],
                            sizeOneElement: this._sizeOneElement
                        })
                            .render();
                        this._subviews[type].$el
                            .appendTo(this.$('.g-search-results-container'));
                    }
                });

                if (_.isEmpty(this._subviews)) {
                    this.$('.g-search-no-results').show();
                }
            });

        return this;
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
        this._query = settings.query;
        this._mode = settings.mode;
        this._type = settings.type;
        this._initResults = settings.initResults || [];
        this._pageLimit = settings.limit || 10;
        this._sizeOneElement = settings.sizeOneElement || 30;

        this._paginateWidget = new SearchPaginateWidget({
            parentView: this,
            type: this._type,
            query: this._query,
            mode: this._mode,
            limit: this._pageLimit
        })
            .on('g:changed', () => {
                this._results = this._paginateWidget.results;
                this.render();
            });

        this._results = this._initResults;
    },

    _getTypeName: function (type) {
        const names = {
            'collection': 'Collections',
            'group': 'Groups',
            'user': 'Users',
            'folder': 'Folders',
            'item': 'Items'
        };
        return names[type] || type;
    },

    _getTypeIcon: function (type) {
        const icons = {
            'user': 'user',
            'group': 'users',
            'collection': 'sitemap',
            'folder': 'folder',
            'item': 'doc-text-inv'
        };
        return icons[type] || 'icon-attention-alt';
    },

    render: function () {
        this.$el.html(SearchResultsTypeTemplate({
            results: this._results,
            collectionName: this._getTypeName(this._type),
            type: this._type,
            icon: this._getTypeIcon(this._type)
        }));

        /* This size of the results list cannot be known until after the fetch completes. And we don't want to set
        the 'min-height' to the max results size, because we'd frequently have lots of whitespace for short result
        lists. Do not try to move that set in stylesheet.
        */
        this.$('.g-search-results-type').css('min-height', `${this._initResults.length * this._sizeOneElement}px`);
        this._paginateWidget
            .setElement(this.$(`#${this._type}Paginate`))
            .render();

        return this;
    }
});

export default SearchResultsView;
