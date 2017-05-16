import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import TaskListWidget from './TaskListWidget';
import ItemTaskCollection from '../collections/ItemTaskCollection';

import template from '../templates/taskListSearchResults.pug';
import '../stylesheets/taskListSearchResults.styl';

/**
 * View for a list of tasks resulting from a text search. The search results are
 * ordered by search score and can be paged through.
 */
var TaskListSearchResultsView = View.extend({
    /*
     * @param {string} settings.q
     *   The search query.
     */
    initialize: function (settings) {
        this.query = settings.q || null;

        this.collection = new ItemTaskCollection();

        // Set the fetch URL to the search endpoint
        this.collection.altUrl = 'item_task/search';

        // Clear the comparator to retain the sort order returned by the
        // search endpoint
        this.collection.comparator = null;

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.taskListWidget = new TaskListWidget({
            collection: this.collection,
            parentView: this
        });

        const params = {
            q: this.query
        };

        this.collection.fetch(params)
            .then(() => {
                this.render();

                // Render PaginateWidget when collection changes
                this.listenTo(this.collection, 'reset', () => {
                    this.paginateWidget.render();
                });
            });
    },

    render: function () {
        this.$el.html(template({
            collection: this.collection,
            query: this.query
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();
        this.taskListWidget.setElement(this.$('.g-task-list-widget-container')).render();

        return this;
    }
});

export default TaskListSearchResultsView;
