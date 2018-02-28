import View from 'girder/views/View';

import PaginateWidgetTemplate from 'girder/templates/widgets/paginateWidget.pug';
import 'girder/stylesheets/widgets/paginateWidget.styl';
/**
 * This widget is used to provide a consistent widget for iterating amongst
 * pages of a Collection.
 */
var PaginateWidget = View.extend({
    events: {
        'click .g-page-next:not(.disabled)': function (e) {
            this.collection.fetchNextPage();
        },
        'click .g-page-prev:not(.disabled)': function (e) {
            this.collection.fetchPreviousPage();
        }
    },

    initialize: function (settings) {
        this.collection = settings.collection;
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
