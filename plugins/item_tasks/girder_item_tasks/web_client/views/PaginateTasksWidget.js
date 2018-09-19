import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import { renderMarkdown } from 'girder/misc';

import ItemTaskCollection from '../collections/ItemTaskCollection';
import template from '../templates/paginateTasksWidget.pug';
import '../stylesheets/paginateTasksWidget.styl';

var PaginateTasksWidget = View.extend({
    events: {
        'click .g-execute-task-link': function (event) {
            const taskId = $(event.currentTarget).data('taskId');
            const task = this.collection.get(taskId);
            this.trigger('g:selected', {
                task: task
            });
        }
    },
    /**
     * @param {Function} [settings.itemUrlFunc] A callback function, which if provided,
     *        will be called with a single ItemModel argument and should return a string
     *        URL to be used as the task link href.
     * @param {ItemTaskCollection} [settings.collection] An ItemTaskCollection for the widget
     *        to display. If no collection is provided, a new ItemTaskCollection is used.
     */
    initialize: function (settings) {
        this.itemUrlFunc = settings.itemUrlFunc || null;
        this.collection = settings.collection || new ItemTaskCollection();
        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this.parentView
        });

        this.listenTo(this.collection, 'g:changed', () => {
            this.render();
        });

        if (settings.collection) {
            this.render();
        } else {
            this.collection.fetch();
        }
    },

    render: function () {
        this.$el.html(template({
            tasks: this.collection.toArray(),
            itemUrlFunc: this.itemUrlFunc,
            renderMarkdown
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();
        return this;
    }
});

export default PaginateTasksWidget;
