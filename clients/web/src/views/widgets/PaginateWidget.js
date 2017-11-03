import View from 'girder/views/View';

import PaginateWidgetTemplate from 'girder/templates/widgets/paginateWidget.pug';

/**
 * This widget is used to provide a consistent widget for iterating amongst
 * pages of a Collection.
 * The parameter "fetchParams" is use to specify a "query" and a "mode" fields
 * in order to do a specific search into a Collection.
 * This is used to perform pagination in the 'SearchResult' view
 */
var PaginateWidget = View.extend({
    events: {
        'click .g-page-next:not(.disabled)': function (e) {
            this.collection.fetchNextPage(this.fetchParams);
        },
        'click .g-page-prev:not(.disabled)': function (e) {
            this.collection.fetchPreviousPage(this.fetchParams);
        }
    },

    initialize: function (settings) {
        this.collection = settings.collection;
        this.fetchParams = settings.fetchParams || {};
    },

    /**
     * Do not call render() until the collection has been fetched once.
     */
    render: function () {
        this.$el.html(PaginateWidgetTemplate({
            collection: this.collection
        }));

        this.$('.g-page-next').girderEnable(this.collection.hasNextPage());
        this.$('.g-page-prev').girderEnable(this.collection.hasPreviousPage());
        return this;
    }
});

export default PaginateWidget;
