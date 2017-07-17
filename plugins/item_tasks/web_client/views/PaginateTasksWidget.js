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
     * @param [settings.hyperlink=false] Whether to create a link that will navigate
     * the user to the specific task's run page. The g:selected event is triggered
     * either way with the taskId passed as a parameter.
     */
    initialize: function (settings) {
        this.collection = new ItemTaskCollection();
        this.hyperlink = settings.hyperlink || false;

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this.parentView
        });

        this.listenTo(this.collection, 'g:changed', () => {
            this.render();
        });
        this.collection.fetch();
    },

    render: function () {
        this.$el.html(template({
            tasks: this.collection.toArray(),
            hyperlink: this.hyperlink
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();

        return this;
    }
});

export default PaginateTasksWidget;
