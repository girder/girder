import $ from 'jquery';
import _ from 'underscore';
// Bootstrap tooltip is required by popover
import 'bootstrap/js/tooltip';
import 'bootstrap/js/popover';

import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';
import router from '@girder/core/router';

import SearchFieldTemplate from '@girder/core/templates/widgets/searchField.pug';
import SearchHelpTemplate from '@girder/core/templates/widgets/searchHelp.pug';
import SearchModeSelectTemplate from '@girder/core/templates/widgets/searchModeSelect.pug';
import SearchResultsTemplate from '@girder/core/templates/widgets/searchResults.pug';
import '@girder/core/stylesheets/widgets/searchFieldWidget.styl';

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

        'click .g-search-result>a': function (e) {
            this._resultClicked($(e.currentTarget));
        },

        'keydown .g-search-field': function (e) {
            var code = e.keyCode || e.which;
            var list, pos;
            if (code === 13 && this.noResourceSelected) { /* enter without resource seleted */
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

        // Do not change the icon for fast searches, to prevent jitter
        this._animatePending = _.debounce(this._animatePending, 100);
    },

    search: function () {
        var q = this.$('.g-search-field').val();

        if (!q) {
            this.hideResults();
            return this;
        }

        if (this.ajaxLock) {
            this.pending = q;
        } else {
            this._doSearch(q);
        }

        return this;
    },

    _goToResultPage: function (query, mode) {
        this.resetState();
        router.navigate(`#search/results?query=${query}&mode=${mode}`, { trigger: true });
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
            currentMode: this.currentMode
        }));

        this.$('.g-search-options-button').popover({
            trigger: 'manual',
            html: true,
            viewport: {
                selector: 'body',
                padding: 10
            },
            content: () => {
                return SearchHelpTemplate({
                    mode: this.currentMode,
                    modeHelp: SearchFieldWidget.getModeHelp(this.currentMode)
                });
            }
        }).click(function () {
            $(this).popover('toggle');
        });

        this.$('.g-search-mode-choose').popover({
            trigger: 'manual',
            html: true,
            viewport: {
                selector: 'body',
                padding: 10
            },
            content: () => {
                return SearchModeSelectTemplate({
                    modes: this.modes,
                    currentMode: this.currentMode,
                    getModeDescription: SearchFieldWidget.getModeDescription
                });
            }
        }).click(function () {
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

    _doSearch: function (q) {
        this.ajaxLock = true;
        this.pending = null;
        this._animatePending();

        restRequest({
            url: 'resource/search',
            data: {
                q: q,
                mode: this.currentMode,
                types: JSON.stringify(_.intersection(
                    this.types,
                    SearchFieldWidget.getModeTypes(this.currentMode))
                )
            }
        }).done((results) => {
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
        });
    }
}, {
    _allowedSearchMode: {},

    addMode: function (mode, types, description, help) {
        if (_.has(SearchFieldWidget._allowedSearchMode, mode)) {
            throw new Error(`The mode "${mode}" exist already. You can't change it`);
        }
        SearchFieldWidget._allowedSearchMode[mode] = {
            'types': types,
            'description': description,
            'help': help
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
