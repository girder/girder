import $ from 'jquery';
import _ from 'underscore';
import View from '@girder/core/views/View';
import HierarchySearchTemplate from '@girder/core/templates/widgets/hierarchySearch.pug';
import SearchResultsTemplate from '@girder/core/templates/widgets/searchResults.pug';

import { restRequest } from '@girder/core/rest';

var HierarchySearchWidget = View.extend({
    events: {
        'input .g-hierarchy-search-field': 'search',
        'click .g-search-result>a': function (e) {
            this._resultClicked($(e.currentTarget));
        },
        'keydown .g-hierarchy-search-field': 'trueSearch'
    },
    initialize: function (settings) {
        this.hierarchyWidget = settings.hierarchyWidget;
        this._defaultFolderModel = settings.folderModel;
    },
    render: function () {
        this.$el.html(HierarchySearchTemplate({
            placeholder: this.currentInput
        }));

        return this;
    },
    /**
     * Function that is called when user clicks search or hits enter to complete search
     * It will edit the current view to have the filtered results instead
     */
    trueSearch: function (e) {
        if (e.keyCode === 13) {
            var q = this.$('.g-hierarchy-search-field').val();
            if (q.length === 0) {
                this.currentInput = '';
            }
            // We can now take the results holder and set the itemWidget to have it as the current view
            const formatQuery = { folderId: { $oid: this._defaultFolderModel.get('_id') }, name: { $regex: `.*${q}.*` } };
            const data = { resourceName: 'item/query', params: { query: JSON.stringify(formatQuery) } };
            this.hideResults();
            this.trigger('g:displaySearchResults', data);
        }
    },
    search: function () {
        var q = this.$('.g-hierarchy-search-field').val();
        this.currentInput = q;
        // If the results are emtpy we reset to the default folder
        if (!q) {
            this.resetState();
            return this;
        }
        if (this.ajaxLock) {
            this.pending = q;
        } else {
            this._doSearch(q);
        }

        return this;
    },
    resetState: function () {
        return this.hideResults().clearText();
    },
    /**
     * Parent views should call this if they wish to hide the result list.
     */
    hideResults: function () {
        this.$('.dropdown').removeClass('open');
        return this;
    },
    clearText: function () {
        this.$('.g-hierarchy-search-field').val('');
        return this;
    },
    _animatePending: function () {
        const isPending = this.ajaxLock;
        this.$('.g-hierarchy-search-state')
            .toggleClass('icon-search', !isPending)
            .toggleClass('icon-spin4 animate-spin', isPending);
    },
    _resultClicked: function (link) {
        if (link.data('resourceType') === 'resultPage') {
            this.trueSearch({ keyCode: 13 });
        } else {
            this.trigger('g:resultClicked', {
                type: link.data('resourceType'),
                id: link.data('resourceId'),
                text: link.text().trim(),
                icon: link.data('resourceIcon')
            });
            this.resetState();
        }
    },
    _doSearch: function (q) {
        this.ajaxLock = true;
        this.pending = null;
        this._animatePending();

        const formatQuery = { folderId: { $oid: this._defaultFolderModel.get('_id') }, name: { $regex: `.*${q}.*` } };
        restRequest({
            url: 'item/query',
            data: {
                query: JSON.stringify(formatQuery)
            }
        }).done((results) => {
            this.ajaxLock = false;
            this._animatePending();
            if (this.pending) {
                this._doSearch(this.pending);
            } else {
                if (!this.$('.g-hierarchy-search-field').val()) {
                    // The search field is empty, so this widget probably had "this.resetState"
                    // called while the search was pending. So, don't render the (now obsolete)
                    // results.
                    return;
                }

                var resources = [];
                this.resultsHolder = results;

                _.each(results, function (result) {
                    var text, icon;
                    if (result._modelType === 'item') {
                        text = result.name;
                        icon = 'doc-text-inv';
                    }
                    resources.push({
                        type: result._modelType,
                        id: result._id,
                        text: text,
                        icon: icon
                    });
                }, this);
                this.$('.g-hierarchy-search-results>ul').html(SearchResultsTemplate({
                    results: resources.slice(0, 6)
                }));
                this.$('.dropdown').addClass('open');
            }
        });
    }
});

export default HierarchySearchWidget;
