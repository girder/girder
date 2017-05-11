import _ from 'underscore';
import View from 'girder/views/View';

import template from '../templates/taskListWidget.pug';
import '../stylesheets/taskListWidget.styl';

/**
 * View that displays a list of item tasks. The list can be paged through.
 * When a search is active, the view displays relevant extra information, such
 * as a note if no matching item tasks were found.
 */
var TaskListWidget = View.extend({
    events: {
        'click .g-task-list-task-items-next-page': function (e) {
            e.preventDefault();
            this.collection.fetchNextPage();
        }
    },

    /**
     * @param {ItemTaskCollection} settings.collection
     *   The collection of item tasks.
     * @param {object} settings.search
     *   Information about the current search. Expected to have the following
     *   properties:
     *   - query {string} - The current search query, or null.
     */
    initialize: function (settings) {
        this.collection = settings.collection;
        this.search = settings.search;
        this.listenTo(this.collection, 'reset', this.render);
    },

    render: function () {
        this.$el.html(template({
            collection: this.collection,
            searching: !_.isNull(this.search.query),
            query: this.search.query
        }));

        return this;
    }
});

export default TaskListWidget;
