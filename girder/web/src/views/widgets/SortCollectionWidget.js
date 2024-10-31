import $ from 'jquery';

import View from '@girder/core/views/View';
import { SORT_ASC, SORT_DESC } from '@girder/core/constants';

import SortCollectionWidgetTemplate from '@girder/core/templates/widgets/sortCollectionWidget.pug';

import 'bootstrap/js/dropdown';

/**
 * This widget is used to provide a consistent widget for sorting
 * pages of a Collection by a chosen field.
 */
var SortCollectionWidget = View.extend({
    events: {
        'click a.g-collection-sort-link': function (event) {
            var sortField = $(event.currentTarget).attr('g-sort');
            this.collection.sortField = sortField;
            this.collection.fetch({}, true);
        },
        'click a.g-sort-order-button': function () {
            if (this.collection.sortDir === SORT_ASC) {
                this.collection.sortDir = SORT_DESC;
            } else {
                this.collection.sortDir = SORT_ASC;
            }
            this.collection.fetch({}, true);
        }
    },

    initialize: function (settings) {
        this.collection = settings.collection;
        this.fields = settings.fields;
    },

    /**
     * Do not call render() until the collection has been fetched once.
     */
    render: function () {
        this.$el.html(SortCollectionWidgetTemplate({
            collection: this.collection,
            fields: this.fields
        }));
        if (this.collection.sortDir === SORT_ASC) {
            this.$('.g-down').addClass('hide');
        } else {
            this.$('.g-up').addClass('hide');
        }
        return this;
    }
});

export default SortCollectionWidget;
