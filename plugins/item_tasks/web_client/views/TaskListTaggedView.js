import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import TaskListWidget from './TaskListWidget';
import ItemTaskCollection from '../collections/ItemTaskCollection';

import template from '../templates/taskListTagged.pug';
import '../stylesheets/taskListTag.styl';
import '../stylesheets/taskListTagged.styl';

/**
 * View for a list of tasks which have all of a list of specified tags. The
 * search results can be paged through.
 */
var TaskListTaggedView = View.extend({
    /*
     * @param {string} settings.tags
     *   A semicolon-delimited list of tags.
     */
    initialize: function (settings) {
        this.tags = settings.tags ? settings.tags.split(';') : null;

        this.collection = new ItemTaskCollection();

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
        });

        this.taskListWidget = new TaskListWidget({
            collection: this.collection,
            parentView: this
        });

        const params = {
            tags: JSON.stringify(this.tags)
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
            tags: this.tags
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();
        this.taskListWidget.setElement(this.$('.g-task-list-widget-container')).render();

        return this;
    }
});

export default TaskListTaggedView;
