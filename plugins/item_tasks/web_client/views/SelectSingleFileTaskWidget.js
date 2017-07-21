import View from 'girder/views/View';

import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

import PaginateTasksWidget from './PaginateTasksWidget';
import ItemTaskCollection from '../collections/ItemTaskCollection';

import SelectTaskViewDialogTemplate from '../templates/selectTaskViewDialog.pug';
import selectTaskViewDescriptionTemplate from '../templates/selectTaskViewTargetDescription.pug';

import '../stylesheets/selectTaskView.styl';

/**
 * A dialog for creating tasks from a specific item.
 */
var SelectSingleFileTaskWidget = View.extend({
    events: {
        'submit #g-select-task-form': function (e) {
            e.preventDefault();
            this.$('.g-submit-select-task').girderEnable(false);
            this.$el.modal('hide');

            this.trigger('g:selected', {
                task: this.task,
                item: this.item
            });
        }
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.collection = new ItemTaskCollection();
        this.collection.pageLimit = 5;
        this.paginateTasksWidget = new PaginateTasksWidget({
            parentView: this,
            collection: this.collection
        }).on('g:selected', this._pickTask, this);
        this.collection.fetch({
            minFileInput: 1,
            maxFileInput: 1
        });
    },

    render: function () {
        this.$el
            .html(SelectTaskViewDialogTemplate({
                item: this.item
            }))
            .girderModal(this);

        this.paginateTasksWidget.setElement(this.$('.g-search-field-container')).render();
        this.$('.g-submit-select-task').girderEnable(false);

        return this;
    },

    _pickTask: function (params) {
        this.task = params.task;
        this.$('.g-submit-select-task').girderEnable(true);

        this.$('.g-target-result-container').html(selectTaskViewDescriptionTemplate({
            task: this.task
        }));
    }
});

export default SelectSingleFileTaskWidget;
