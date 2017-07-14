import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';

import ItemTaskCollection from '../collections/ItemTaskCollection';
import template from '../templates/paginateTasksWidget.pug';
import '../stylesheets/paginateTasksWidget.styl';

var PaginateTasksWidget = View.extend({
    events: {
        'click .g-execute-task-link': function (event) {
            let taskId = $(event.currentTarget).data('taskId');

            this.trigger('g:selected', {
                taskId: taskId
            });
        }
    },

    initialize: function (params) {
        this.collection = new ItemTaskCollection();

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
            tasks: this.collection.toArray()
        }));

        this.paginateWidget.setElement(this.$('.g-task-pagination')).render();

        return this;
    }
});

export default PaginateTasksWidget;
