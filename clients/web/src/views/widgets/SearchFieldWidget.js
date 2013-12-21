/**
 * This widget provides a text field that will search any set of data types
 * and show matching results as the user types. Results can be clicked,
 * triggering a callback.
 */
girder.views.SearchFieldWidget = Backbone.View.extend({
    events: {
        'input .g-search-field': function () {
            var q = this.$('.g-search-field').val();

            if (!q) {
                this.$('.dropdown').removeClass('open');
                return;
            }

            if (this.ajaxLock) {
                this.pending = q;
            }
            else {
                this._doSearch(q);
            }
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
                list.html(jade.templates.searchResults({
                    results: results
                }));

                this.$('.dropdown').addClass('open');
            }
        }, this));
    }
});
