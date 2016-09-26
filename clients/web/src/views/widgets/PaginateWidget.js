import View from 'girder/views/View';

import PaginateWidgetTemplate from 'girder/templates/widgets/paginateWidget.pug';

/**
 * This widget is used to provide a consistent widget for iterating amongst
 * pages of a Collection.
 */
var PaginateWidget = View.extend({
    events: {
        'click .g-page-next': function (e) {
            if (!$(e.currentTarget).hasClass('disabled')) {
                this.collection.fetchNextPage();
            }
        },
        'click .g-page-prev': function (e) {
            if (!$(e.currentTarget).hasClass('disabled')) {
                this.collection.fetchPreviousPage();
            }
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

        if (this.collection.hasNextPage()) {
            this.$('.g-page-next').removeClass('disabled');
        } else {
            this.$('.g-page-next').addClass('disabled');
        }

        if (this.collection.hasPreviousPage()) {
            this.$('.g-page-prev').removeClass('disabled');
        } else {
            this.$('.g-page-prev').addClass('disabled');
        }
        return this;
    }
});

export default PaginateWidget;
