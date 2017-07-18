import View from 'girder/views/View';
import router from 'girder/router';

import PaginateTasksWidget from './PaginateTasksWidget';

var TaskListView = View.extend({
    initialize: function () {
        this.paginateWidget = new PaginateTasksWidget({
            el: this.$el,
            parentView: this,
            itemUrlFunc: (task) => {
                return `#item_task/${task.id}/run`;
            }
        }).once('g:selected', function (params) {
            const taskId = params.task.id;
            router.navigate(`item_task/${taskId}/run`, {trigger: true});
        });
    }
});

export default TaskListView;
