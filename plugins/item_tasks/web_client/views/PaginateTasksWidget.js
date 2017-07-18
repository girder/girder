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
     * @param [settings.itemUrlFunc=null] A callback function, which if provided,
     * takes a single item_task model argument and returns a string URL to be used
     * as the task link href.
     * @param [settings.params={}] Any additional parameters to be passed with the fetch request.
     */
    initialize: function (settings) {
        this.itemUrlFunc = settings.itemUrlFunc || null;
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
            itemUrlFunc: this.itemUrlFunc
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();

        return this;
    }
});

export default PaginateTasksWidget;
