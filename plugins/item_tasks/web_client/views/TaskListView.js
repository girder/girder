import View from 'girder/views/View';
import ItemCollection from 'girder/collections/ItemCollection';
import PaginateWidget from 'girder/views/widgets/PaginateWidget';

import template from '../templates/taskList.pug';

var TaskListView = View.extend({
    initialize: function () {
        this.collection = new ItemCollection();
        this.collection.altUrl = 'item_task';

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
            tasks: this.collection.models
        }));

        this.paginateWidget.setElement(this.$('.g-paginate-container')).render();
    }
});

export default TaskListView;
