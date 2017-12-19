import $ from 'jquery';
import _ from 'underscore';
// Bootstrap tooltip is required by popover
import 'bootstrap/js/tooltip';
import 'bootstrap/js/popover';

import View from 'girder/views/View';
import { restRequest } from 'girder/rest';

import SearchFieldTemplate from 'girder/templates/widgets/searchField.pug';
import SearchHelpTemplate from 'girder/templates/widgets/searchHelp.pug';
import SearchModeSelectTemplate from 'girder/templates/widgets/searchModeSelect.pug';
import SearchResultsTemplate from 'girder/templates/widgets/searchResults.pug';

import 'girder/stylesheets/widgets/searchFieldWidget.styl';

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

            window.setTimeout(_.bind(function () {
                this.$('.g-search-mode-choose').popover('hide');
            }, this), 250);
        },

        'click .g-search-result>a': function (e) {
            this._resultClicked($(e.currentTarget));
        },

        'keydown .g-search-field': function (e) {
            var code = e.keyCode || e.which;
            var list, pos;
            if (code === 40) { /* down arrow */
                list = this.$('.g-search-result');
                pos = list.index(list.filter('.g-search-selected')) + 1;
                list.removeClass('g-search-selected');
                if (pos < list.length) {
                    list.eq(pos).addClass('g-search-selected');
                }
            } else if (code === 38) { /* up arrow */
                list = this.$('.g-search-result');
                pos = list.index(list.filter('.g-search-selected')) - 1;
                list.removeClass('g-search-selected');
                if (pos === -2) {
                    pos = list.length - 1;
                }
                if (pos >= 0) {
                    list.eq(pos).addClass('g-search-selected');
                }
            } else if (code === 13) { /* enter */
                e.preventDefault();
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
     */
    initialize: function (settings) {
        this.ajaxLock = false;
        this.pending = null;

        this.placeholder = settings.placeholder || 'Search...';
        this.getInfoCallback = settings.getInfoCallback || null;
        this.types = settings.types || [];
        this.modes = settings.modes || SearchFieldWidget.getModes();

        if (!_.isArray(this.modes)) {
            this.modes = [this.modes];
        }

        this.currentMode = this.modes[0];
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

    _resultClicked: function (link) {
        this.trigger('g:resultClicked', {
            type: link.attr('resourcetype'),
            id: link.attr('resourceid'),
            text: link.text().trim(),
            icon: link.attr('g-icon')
        });
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
            content: _.bind(function () {
                return SearchHelpTemplate({
                    mode: this.currentMode,
                    modeHelp: SearchFieldWidget.getModeHelp(this.currentMode)
                });
            }, this)
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
            content: _.bind(function () {
                return SearchModeSelectTemplate({
                    modes: this.modes,
                    currentMode: this.currentMode,
                    getModeDescription: SearchFieldWidget.getModeDescription
                });
            }, this)
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

    _doSearch: function (q) {
        this.ajaxLock = true;
        this.pending = null;

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
        }).done(_.bind(function (results) {
            this.ajaxLock = false;

            if (this.pending) {
                this._doSearch(this.pending);
            } else {
                var list = this.$('.g-search-results>ul');
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
                list.html(SearchResultsTemplate({
                    results: resources
                }));

                this.$('.dropdown').addClass('open');
            }
        }, this));
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
