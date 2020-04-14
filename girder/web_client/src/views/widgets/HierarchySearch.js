import $ from 'jquery';
import _ from 'underscore';
import View from '@girder/core/views/View';
import { restRequest } from '@girder/core/rest';


var HierarchyPaginatedView = View.extend({
    events: {
        'change #g-page-selection-input': function (event) {
            this.itemListWidget.setPage(Number(event.target.value));
        }
    },
    initialize: function (settings) {
        this.itemListWidget = settings.itemListWidget;
    },
    render: function () {
        this.$el.html(HierarchyPaginatedTemplate({
            totalPages: this.itemListWidget && this.itemListWidget.getNumPages(),
            currentPage: this.itemListWidget && this.itemListWidget.getCurrentPage()
        }));

        return this;
    }
});