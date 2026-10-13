import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
// Bootstrap tooltip is required by popover
import 'bootstrap/js/tooltip';
import 'bootstrap/js/popover';

import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';
import router from '@girder/core/router';

import SearchFieldTemplate from '@girder/core/templates/widgets/searchField.pug';
import SearchHelpTemplate from '@girder/core/templates/widgets/searchHelp.pug';
import SearchModeSelectTemplate from '@girder/core/templates/widgets/searchModeSelect.pug';
import SearchResultsTemplate from '@girder/core/templates/widgets/searchResults.pug';
import '@girder/core/stylesheets/widgets/searchFieldWidget.styl';

/**
 * The last hierarchy location the user visited, shared by all search fields. Local searches use it
 * on pages that aren't hierarchy locations, like the search results page.
 */
let lastHierarchyParent = null;

/**
 * Parse a hierarchy location from a route fragment.
 *
 * @returns An object with "type" and "id", or null.
 */
function parseHierarchyParent(fragment) {
    const parts = (fragment || '').split('?')[0].split('/');
    let parent = null;

    for (let i = 0; i + 1 < parts.length; i += 2) {
        if (!_.contains(['collection', 'folder', 'user'], parts[i]) ||
                !/^[0-9a-fA-F]{24}$/.test(parts[i + 1])) {
            return null;
        }
        parent = { type: parts[i], id: parts[i + 1] };
    }
    return parent;
}

/**
 * Remember the current route if it's a hierarchy location, and return the last one.
 */
function activeHierarchyParent() {
    const current = parseHierarchyParent(Backbone.history.fragment);
    if (current) {
        lastHierarchyParent = current;
    }
    return lastHierarchyParent;
}

// Browsing the hierarchy updates the route without triggering it, so track it here too.
events.on('g:hierarchy.route', () => {
    activeHierarchyParent();
});

// Forget the location on login or logout, since it may belong to someone else.
events.on('g:login', () => {
    lastHierarchyParent = null;
});

/**
 * This widget provides a text field that will search any set of data types
 * and show matching results as the user types. Results can be clicked,
 * triggering a callback.
 */
var SearchFieldWidget = View.extend({
    events: {
        'input .g-search-field': 'search',

        'click .g-search-mode-radio': function (e) {
            this.currentMode = $(e.target).val();
            this.hideResults().search();

            window.setTimeout(() => {
                this.$('.g-search-mode-choose').popover('hide');
            }, 250);
        },

        'change .g-search-local-checkbox': function (e) {
            this.localSearch = $(e.target).prop('checked');
            this.hideResults().search();

            window.setTimeout(() => {
                this.$('.g-search-mode-choose').popover('hide');
            }, 250);
        },

        'click .g-search-result>a': function (e) {
            this._resultClicked($(e.currentTarget));
        },

        'keydown .g-search-field': function (e) {
            var code = e.keyCode || e.which;
            var list, pos;
            if (code === 13 && this.noResourceSelected) { /* enter without resource selected */
                e.preventDefault();
                if (this.$('.g-search-field').val() !== '' && !this.noResultsPage) {
                    this._goToResultPage(this.$('.g-search-field').val(), this.currentMode);
                }
            } else if (code === 40 || code === 38) {
                this.noResourceSelected = false;
                if (code === 40) { /* down arrow */
                    list = this.$('.g-search-result');
                    pos = list.index(list.filter('.g-search-selected')) + 1;
                    list.removeClass('g-search-selected');
                    if (pos < list.length) {
                        list.eq(pos).addClass('g-search-selected');
                    }
                    if (pos === list.length) {
                        this.noResourceSelected = true;
                    }
                } else if (code === 38) { /* up arrow */
                    list = this.$('.g-search-result');
                    pos = list.index(list.filter('.g-search-selected')) - 1;
                    list.removeClass('g-search-selected');
                    if (pos === -1) {
                        this.noResourceSelected = true;
                    }
                    if (pos === -2) {
                        pos = list.length - 1;
                    }
                    if (pos >= 0) {
                        list.eq(pos).addClass('g-search-selected');
                    }
                }
            } else if (code === 13) { /* enter with resource selected */
                e.preventDefault();
                this.noResourceSelected = true;
                var link = this.$('.g-search-result.g-search-selected>a');
                if (link.length) {
                    this._resultClicked(link);
                }
            }
        }
    },

    /**
     * @param [settings.placeholder="Search..."] The placeholder text for the input field.
     * @param [settings.getInfoCallback] For custom resource types, this callback can
     *        be passed in to resolve their title and icon. This callback should
     *        return an object with "icon" and "text" fields if it can resolve
     *        the result, or return falsy otherwise.
     * @param [settings.modes=["text", "prefix"]] A string or list of strings
     *        representing the allowed search modes. Supported modes: "text", "prefix".
     *        If multiple are allowed, users are able to select which one to use
     *        via a dropdown.
     * @param [settings.noResultsPage=false] If truthy, don't jump to a results
     *        page if enter is typed with a list of search results.
     * @param [settings.localSearch=false] If truthy, start with "Search here" checked.
     */
    initialize: function (settings) {
        this.ajaxLock = false;
        this.pending = null;
        this.noResourceSelected = true;
        this.placeholder = settings.placeholder || 'Search...';
        this.noResultsPage = settings.noResultsPage || false;
        this.getInfoCallback = settings.getInfoCallback || null;
        /* The order of settings.types give the order of the display of the elements :
         *     ['collection', 'folder', 'item'] will be render like this
         *       [icon-collection] Collections..
         *       [icon-folder] Folders..
         *       [icon-item] Items..
         */
        this.types = settings.types || [];
        this.modes = settings.modes || SearchFieldWidget.getModes();

        if (!_.isArray(this.modes)) {
            this.modes = [this.modes];
        }

        this.currentMode = this.modes[0];

        // Only offer "Search here" for types that live in the hierarchy.
        this.localSearchSupported = !_.isEmpty(
            _.intersection(this.types, SearchFieldWidget.hierarchyTypes));
        this.localSearch = this.localSearchSupported && !!settings.localSearch;

        // Do not change the icon for fast searches, to prevent jitter
        this._animatePending = _.debounce(this._animatePending, 100);
    },

    /**
     * The location to restrict the search to, or null.
     */
    _localSearchParent: function () {
        const parent = activeHierarchyParent();
        return this.localSearch ? parent : null;
    },

    search: function () {
        var query = this.$('.g-search-field').val();

        if (!query) {
            this.hideResults();
            return this;
        }

        if (this.ajaxLock) {
            this.pending = query;
        } else {
            this._doSearch(query);
        }

        return this;
    },

    _goToResultPage: function (query, mode) {
        // Get the location first, since the results page isn't a hierarchy location.
        const parent = this._localSearchParent();
        this.resetState();
        let route = `#search/results?query=${query}&mode=${mode}`;
        if (parent) {
            route += `&parentType=${parent.type}&parentId=${parent.id}`;
        }
        router.navigate(route, { trigger: true });
    },

    _resultClicked: function (link) {
        if (link.data('resourceType') === 'resultPage') {
            this._goToResultPage(this.$('.g-search-field').val(), this.currentMode);
        } else {
            this.trigger('g:resultClicked', {
                type: link.data('resourceType'),
                id: link.data('resourceId'),
                text: link.text().trim(),
                icon: link.data('resourceIcon')
            });
        }
    },

    render: function () {
        this.$el.html(SearchFieldTemplate({
            placeholder: this.placeholder,
            modes: this.modes,
            currentMode: this.currentMode,
            localSearchSupported: this.localSearchSupported
        }));

        this.$('.g-search-options-button').popover({
            trigger: 'manual',
            viewport: {
                selector: 'body',
                padding: 10
            },
            content: () => {
                return SearchHelpTemplate({
                    mode: this.currentMode,
                    modeHelp: SearchFieldWidget.getModeHelp(this.currentMode)
                });
            },
            html: true,
            sanitize: false
        }).on('click', function () {
            $(this).popover('toggle');
        });

        this.$('.g-search-mode-choose').popover({
            trigger: 'manual',
            viewport: {
                selector: 'body',
                padding: 10
            },
            content: () => {
                return SearchModeSelectTemplate({
                    modes: this.modes,
                    currentMode: this.currentMode,
                    getModeDescription: SearchFieldWidget.getModeDescription,
                    localSearchSupported: this.localSearchSupported,
                    localSearch: this.localSearch
                });
            },
            html: true,
            sanitize: false
        }).on('click', function () {
            $(this).popover('toggle');
        });

        return this;
    },

    /**
     * Parent views should call this if they wish to hide the result list.
     */
    hideResults: function () {
        this.$('.dropdown').removeClass('open');
        return this;
    },

    /**
     * Parent views should call this if they wish to clear the search text.
     */
    clearText: function () {
        this.$('.g-search-field').val('');
        return this;
    },

    /**
     * Parent views should call this if they wish to reset the search widget,
     * i.e. clear it and hide any results.
     */
    resetState: function () {
        return this.hideResults().clearText();
    },

    _animatePending: function () {
        const isPending = this.ajaxLock;
        this.$('.g-search-state')
            .toggleClass('icon-search', !isPending)
            .toggleClass('icon-spin4 animate-spin', isPending);
    },

    _doSearch: function (query) {
        this.ajaxLock = true;
        this.pending = null;
        this._animatePending();

        const data = {
            q: query,
            mode: this.currentMode,
            types: JSON.stringify(_.intersection(
                this.types,
                SearchFieldWidget.getModeTypes(this.currentMode))
            )
        };
        const parent = this._localSearchParent();
        if (parent) {
            data.parentType = parent.type;
            data.parentId = parent.id;
        }

        const request = {
            url: 'resource/search',
            data: data
        };
        if (parent) {
            // Handle errors below, rather than alerting on every keystroke.
            request.error = null;
        }
        restRequest(request).done((results) => {
            this.ajaxLock = false;
            this._animatePending();

            if (this.pending) {
                this._doSearch(this.pending);
            } else {
                if (!this.$('.g-search-field').val()) {
                    // The search field is empty, so this widget probably had "this.resetState"
                    // called while the search was pending. So, don't render the (now obsolete)
                    // results.
                    return;
                }

                var resources = [];
                _.each(this.types, function (type) {
                    _.each(results[type] || [], function (result) {
                        var text, icon;
                        if (type === 'user') {
                            text = result.firstName + ' ' + result.lastName +
                                ' (' + result.login + ')';
                            icon = 'user';
                        } else if (type === 'group') {
                            text = result.name;
                            icon = 'users';
                        } else if (type === 'collection') {
                            text = result.name;
                            icon = 'sitemap';
                        } else if (type === 'folder') {
                            text = result.name;
                            icon = 'folder';
                        } else if (type === 'item') {
                            text = result.name;
                            icon = 'doc-text-inv';
                        } else {
                            if (this.getInfoCallback) {
                                var res = this.getInfoCallback(type, result);
                                if (res) {
                                    text = res.text;
                                    icon = res.icon;
                                }
                            }
                            if (!text || !icon) {
                                text = '[unknown type]';
                                icon = 'attention';
                            }
                        }
                        resources.push({
                            type: type,
                            id: result._id,
                            text: text,
                            icon: icon
                        });
                    }, this);
                }, this);
                this.$('.g-search-results>ul').html(SearchResultsTemplate({
                    results: resources.slice(0, 6)
                }));
                this.$('.dropdown').addClass('open');
            }
        }).fail(() => {
            this.ajaxLock = false;
            this._animatePending();

            if (this.pending) {
                this._doSearch(this.pending);
            } else if (parent && this.$('.g-search-field').val()) {
                // The location may be gone, or no longer accessible, so stop searching it.
                lastHierarchyParent = null;
                this.$('.g-search-results>ul').html(SearchResultsTemplate({
                    results: [],
                    message: 'Can\'t search here'
                }));
                this.$('.dropdown').addClass('open');
            }
        });
    }
}, {
    _allowedSearchMode: {},

    /**
     * The types that "Search here" can restrict.
     */
    hierarchyTypes: ['folder', 'item'],

    addMode: function (mode, types, description, help) {
        if (_.has(SearchFieldWidget._allowedSearchMode, mode)) {
            throw new Error(`The mode "${mode}" exist already. You can't change it`);
        }
        SearchFieldWidget._allowedSearchMode[mode] = {
            types: types,
            description: description,
            help: help
        };
    },

    getModes: function () {
        return _.keys(SearchFieldWidget._allowedSearchMode);
    },

    getModeTypes: function (mode) {
        return SearchFieldWidget._allowedSearchMode[mode].types;
    },

    getModeDescription: function (mode) {
        return SearchFieldWidget._allowedSearchMode[mode].description;
    },

    getModeHelp: function (mode) {
        return SearchFieldWidget._allowedSearchMode[mode].help;
    },

    removeMode: function (mode) {
        delete SearchFieldWidget._allowedSearchMode[mode];
    }
});

SearchFieldWidget.addMode(
    'text',
    ['item', 'folder', 'group', 'collection', 'user'],
    'Full text search',
    `By default, search results will be returned if they contain
     any of the terms of the search. If you wish to search for documents
     containing all of the terms, place them in quotes.
     Examples:`
);
SearchFieldWidget.addMode(
    'prefix',
    ['item', 'folder', 'group', 'collection', 'user'],
    'Search by prefix',
    `You are searching by prefix.
     Start typing the first letters of whatever you are searching for.`
);
export default SearchFieldWidget;
