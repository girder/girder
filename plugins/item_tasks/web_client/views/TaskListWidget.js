import View from 'girder/views/View';

import template from '../templates/taskListWidget.pug';
import '../stylesheets/taskListTag.styl';
import '../stylesheets/taskListWidget.styl';

/**
 * View that displays a list of item tasks.
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
     */
    initialize: function (settings) {
        this.listenTo(this.collection, 'reset', this.render);
    },

    render: function () {
        this.$el.html(template({
            collection: this.collection
        }));

        return this;
    }
});

export default TaskListWidget;
