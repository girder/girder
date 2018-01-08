import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import router from 'girder/router';
import SearchResultsTemplate from 'girder/templates/body/searchResults.pug';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
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
        this.pageLimit = 5;
        this._query = settings.query;
        this._mode = settings.mode;
        this._types = settings.types || ['collection', 'group', 'user', 'folder', 'item'];

        this._collections = {
            'collection': new CollectionCollection(),
            'group': new GroupCollection(),
            'user': new UserCollection()
            // Wait the PR : search mode set to fetch collection
            // 'folder': new FolderCollection(),
            // 'item': new ItemCollection()
        };

        this.paginateWidgets = {};

        let _collectionsPaginateTmp = null;
        let res = null;
        let type = null;

        _.each(this._collections, (collection) => {
            collection.pageLimit = this.pageLimit;
            collection.on('g:changed', function () {
                res = this.parseCollection(collection);
                this.parseResults(res);
                this.render();
            }, this).fetch();

            _collectionsPaginateTmp = new PaginateWidget({
                parentView: this,
                collection: collection
                // ADD new changes of search in fetch.
                // Wait the PR to be merge
                /*
                fetchParams = {
                    query: this._query,
                    mode: this._mode
                }
                */
            });
            type = _.findKey(this._collections, collection);
            this.paginateWidgets[type] = _collectionsPaginateTmp;
        });

        this.render();
    },

    parseResults: function (res) {
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

    parseCollection: function (collection) {
        let icon;
        let type;
        for (let key in this._collections) {
            if (this._collections[key] === collection) {
                type = key;
            }
        }
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
            'elements': this._collections[type].toArray()
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
        this.$el.html(SearchResultsTemplate({
            results: this.results || null,
            query: this._query || null,
            length: this.results.length || 0
        }));

        // set paginateWidget only for results types containing elements
        _.each(this.results, (result) => {
            for (var key in this.paginateWidgets) {
                if (result.type === key && (
                        this.paginateWidgets[key].collection.hasNextPage() ||
                        this.paginateWidgets[key].collection.hasPreviousPage())) {
                    this.paginateWidgets[key].setElement(this.$(`#${result.type}Paginate`)).render();
                }
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

export default SearchResultsView;
