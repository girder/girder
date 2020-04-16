import $ from 'jquery';
import _ from 'underscore';
import View from '@girder/core/views/View';
import SearchResultsTemplate from '@girder/core/templates/widgets/searchResults.pug';
import { restRequest } from '@girder/core/rest';


var HierarchySearchView = View.extend({
    events: {
        'input .g-hierarchy-search-field': 'search'
    },
    initialize: function (settings) {
        this.itemListWidget = settings.itemListWidget;
        this.hierarchyWidget = settings.hierarchyWidget;
        this._defaultFolderModel = settings.folderModel;
    },
    render: function () {
        this.$el.html(HierarchyPaginatedTemplate({
            totalPages: this.itemListWidget && this.itemListWidget.getNumPages(),
            currentPage: this.itemListWidget && this.itemListWidget.getCurrentPage()
        }));

        return this;
    },
    search: function () {
        var q = this.$('.g-search-field').val();

        //If the results are emtpy we reset to the default folder
        if (!q) {
            this.resetItemList();
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
    _animatePending: function () {
        const isPending = this.ajaxLock;
        this.$('.g-hierarchy-search-state')
            .toggleClass('icon-search', !isPending)
            .toggleClass('icon-spin4 animate-spin', isPending);
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
    _doSearch: function (q) {
        this.ajaxLock = true;
        this.pending = null;
        this._animatePending();

        const formatQuery = { '$oid': this.folderId, "name":{"$regex":`.*${q}.*`}};
        restRequest({
            url: 'item/query',
            data: {
                query: q,
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
                _.each(this.types, function (type) {
                    _.each(results[type] || [], function (result) {
                        var text, icon;
                         if (type === 'item') {
                            text = result.name;
                            icon = 'doc-text-inv';
                        } 
                        resources.push({
                            type: type,
                            id: result._id,
                            text: text,
                            icon: icon
                        });
                    }, this);
                }, this);
                this.$('.g-hierarchy-search-results>ul').html(SearchResultsTemplate({
                    results: resources.slice(0, 6)
                }));
                this.$('.dropdown').addClass('open');
            }
        });
    }
});