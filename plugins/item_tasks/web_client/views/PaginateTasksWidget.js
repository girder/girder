import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';

import ItemTaskCollection from '../collections/ItemTaskCollection';
import template from '../templates/paginateTasksWidget.pug';
import '../stylesheets/paginateTasksWidget.styl';

var PaginateTasksWidget = View.extend({
    events: {
        'click .g-execute-task-link': function (event) {
            const taskId = $(event.currentTarget).data('taskId');
            this.trigger('g:selected', {
                taskId: taskId
            });
        }
    },
    /**
     * @param [settings.hyperlinkCallback=null] A callback function, which if provided,
     * takes a single task argument (of an item_task model) and returns a string
     * of a URL to be used as the task link href. The g:selected event is triggered
     * either way with the taskId passed as a parameter.
     * @param params Any additional parameters to be passed with the fetch request.
     */
    initialize: function (settings) {
        this.hyperlinkCallback = settings.hyperlinkCallback || null;
        this.params = settings.fetchParams || {};
        this.collection = new ItemTaskCollection();
        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this.parentView
        });

        this.listenTo(this.collection, 'g:changed', () => {
            this.render();
        });
        this.collection.fetch(this.params);
    },

    render: function () {
        this.$el.html(template({
            tasks: this.collection.toArray(),
            hyperlinkCallback: this.hyperlinkCallback
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();

        return this;
    }
});

export default PaginateTasksWidget;
