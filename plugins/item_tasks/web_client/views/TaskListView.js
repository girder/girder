import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import TaskListWidget from './TaskListWidget';
import ItemTaskCollection from '../collections/ItemTaskCollection';

import template from '../templates/taskList.pug';
import '../stylesheets/taskList.styl';

/**
 * View for a list of tasks. By default all available tasks are listed and can
 * be paged through. The user can search for tasks using a search box. The
 * search results are ordered by search score and can be paged through.
 */
var TaskListView = View.extend({
    events: {
        'submit .g-task-search-form': function (e) {
            e.preventDefault();
            let query = this.$('.g-task-search-field').val().trim();
            if (query) {
                this._search(query);
            } else {
                this._resetSearch();
            }
        }
    },

    initialize: function () {
        this.collection = new ItemTaskCollection();

        // Store collection parameters that search mode overrides
        this.originalCollectionParameters = {
            altUrl: this.collection.altUrl,
            comparator: this.collection.comparator
        };

        this.search = {query: null};

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.taskListWidget = new TaskListWidget({
            collection: this.collection,
            search: this.search,
            parentView: this
        });

        this.collection.fetch()
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
            tasks: this.collection.models
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();
        this.taskListWidget.setElement(this.$('.g-task-list-widget-container')).render();

        return this;
    },

    /**
     * Clear the results of a search.
     */
    _resetSearch: function () {
        this.search.query = null;

        // Reset collection to original state
        this.collection.altUrl = this.originalCollectionParameters.altUrl;
        this.collection.comparator = this.originalCollectionParameters.comparator;
        this.collection.params = {};
        this.collection.fetch(null, true);
    },

    /**
     * Perform a search request.
     * @param {string} query The search query.
     */
    _search: function (query) {
        this.search.query = query;

        // Set the fetch URL to the search endpoint
        this.collection.altUrl = 'item_task/search';

        // Clear the comparator to retain the sort order returned by the
        // search endpoint
        this.collection.comparator = null;

        this.collection.params = {q: query};
        this.collection.fetch(null, true);
    }
});

export default TaskListView;
