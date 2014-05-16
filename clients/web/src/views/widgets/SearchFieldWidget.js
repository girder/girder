/**
 * This widget provides a text field that will search any set of data types
 * and show matching results as the user types. Results can be clicked,
 * triggering a callback.
 */
girder.views.SearchFieldWidget = girder.View.extend({
    events: {
        'input .g-search-field': function () {
            var q = this.$('.g-search-field').val();

            if (!q) {
                this.hideResults();
                return;
            }

            if (this.ajaxLock) {
                this.pending = q;
            }
            else {
                this._doSearch(q);
            }
        },
        'click .g-search-result>a': function (e) {
            var link = $(e.currentTarget);

            this.trigger('g:resultClicked', {
                type: link.attr('resourcetype'),
                id: link.attr('resourceid'),
                text: link.text()
            });
        }
    },

    initialize: function (settings) {
        this.ajaxLock = false;
        this.pending = null;

        this.placeholder = settings.placeholder || 'Search...';
        this.types = settings.types || [];
    },

    render: function () {
        this.$el.html(jade.templates.searchField({
            placeholder: this.placeholder
        }));

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

        girder.restRequest({
            path: 'resource/search',
            data: {
                q: q,
                types: JSON.stringify(this.types)
            }
        }).done(_.bind(function (results) {
            this.ajaxLock = false;

            if (this.pending) {
                this._doSearch(this.pending);
            }
            else {
                var list = this.$('.g-search-results>ul');
                var resources = [];
                _.each(this.types, function (type) {
                    _.each(results[type] || [], function (result) {
                        var text, icon;
                        if (type === 'user') {
                            text = result.firstName + ' ' + result.lastName +
                                ' (' + result.login + ')';
                            icon = 'user';
                        }
                        else if (type === 'group') {
                            text = result.name;
                            icon = 'users';
                        }
                        else if (type === 'collection') {
                            text = result.name;
                            icon = 'sitemap';
                        }
                        else if (type === 'folder') {
                            text = result.name;
                            icon = 'folder';
                        }
                        else if (type === 'item') {
                            text = result.name;
                            icon = 'doc-text-inv';
                        }
                        else {
                            // TODO plugin callback to render results
                            text = '[unknown type]';
                            icon = 'attention';
                        }
                        resources.push({
                            type: type,
                            id: result._id,
                            text: text,
                            icon: icon
                        });
                    }, this);
                }, this);
                list.html(jade.templates.searchResults({
                    results: resources
                }));

                this.$('.dropdown').addClass('open');
            }
        }, this));
    }
});
