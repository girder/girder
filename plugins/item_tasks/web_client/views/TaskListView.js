import View from 'girder/views/View';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';
import ItemTaskCollection from '../collections/ItemTaskCollection';

import template from '../templates/taskList.pug';
import '../stylesheets/taskList.styl';

var TaskListView = View.extend({
    initialize: function () {
        this.collection = new ItemTaskCollection();

        this.paginateWidget = new PaginateWidget({
            collection: this.collection,
            parentView: this
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
    }
});

export default TaskListView;
