import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import router from 'girder/router';
import SearchResultsTemplate from 'girder/templates/body/searchResults.pug';
import SearchPaginateWidget from 'girder/views/widgets/SearchPaginateWidget';
import CollectionCollection from 'girder/collections/CollectionCollection';
import GroupCollection from 'girder/collections/GroupCollection';
import UserCollection from 'girder/collections/UserCollection';
/* import FolderCollection from 'girder/collections/FolderCollection';
import ItemCollection from 'girder/collections/ItemCollection'; */
import 'girder/stylesheets/body/searchResultsList.styl';

/**
 * This view display all the search results per each type
 */
var SearchResultsView = View.extend({
    events: {
        'click .g-search-result>a': function (e) {
            this._resultClicked($(e.currentTarget));
        }
    },

    initialize: function (settings) {
        this.results = [];
        this.pageLimit = 2;
        this._query = settings.query;
        this._mode = settings.mode;
        this._types = settings.types || ['collection', 'group', 'user', 'folder', 'item'];

        this.paginateWidgets = {};

        let _paginateTmp = null;
        let res = null;
        let type = null;

        _.each(this._types, (type) => {
            _paginateTmp = new SearchPaginateWidget({
                parentView: this,
                type: [type],
                query: this._query,
                mode: this._mode,
                limit: this.pageLimit
            });
            this.paginateWidgets[type] = _paginateTmp;
            _paginateTmp.on(`g:changed_${type}`,  function () {
                var results = this.parseCollection(
                    this.paginateWidgets[type].results,
                    type);
                console.log(results);
                this.updateResults(results);
                this.render();
            }, this)
        });
    },

    updateResults: function (res) {
        let notIn = 0;

        for (let i = 0; i < this.results.length; i++) {
            if (res.type === this.results[i].type) {
                this.results[i] = res;
            } else {
                notIn++;
            }
        }
        if (notIn === this.results.length) {
            this.results.push(res);
        }
    },

    parseCollection: function (rawResults, type) {
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
        return {
            'type': type,
            'icon': icon,
            'elements': rawResults
        };
    },

    render: function () {
        /** The 'SearchResutlsTemplate' need a results parameters as :
         *  [{
         *      'type': type,
         *      'icon': icon,
         *      'elements': [obj, ...]
         *   }, ... ]
         */

        // TODO: Fix the name issue of the user
        // TODO: Remove result header when no element inside
        // TODO: Fix the order of display --> Collection, folder, item, user, group ?
        this.$el.html(SearchResultsTemplate({
            results: this.results || null,
            query: this._query || null,
            length: this.results.length || 0
        }));

        // set paginateWidget only for results types containing elements
         // && (
         //                this.paginateWidgets[key].hasNextPage() ||
         //                this.paginateWidgets[key].hasPreviousPage())
        if (this.results.length === this._types.length) {
            console.log('res', this.results);
            _.each(this.results, (result) => {
                for (var key in this.paginateWidgets) {
                    if (result.type === key) {
                        console.log(key, this.paginateWidgets[key].hasNextPage());
                        this.paginateWidgets[key].setElement(this.$(`#${result.type}Paginate`)).render();
                    }
                }
            });
        }


        return this;
    },

    _resultClicked: function (result) {
        router.navigate(result.attr('resourcetype') + '/' + result.attr('resourceid'), {
            trigger: true
        });
    }
});

export default SearchResultsView;
