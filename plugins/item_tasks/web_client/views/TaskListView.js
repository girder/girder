import View from 'girder/views/View';
import router from 'girder/router';

import ItemTaskCollection from '../collections/ItemTaskCollection';
import PaginateTasksWidget from './PaginateTasksWidget';

var TaskListView = View.extend({
    initialize: function () {
        this.paginateWidget = new PaginateTasksWidget({
            el: this.$el,
            parentView: this
        }).once('g:selected', function(params) {
            let taskId = params.taskId;
            router.navigate('item_task/' + taskId + '/run', {trigger: true});
        });
    }
});

export default TaskListView;
