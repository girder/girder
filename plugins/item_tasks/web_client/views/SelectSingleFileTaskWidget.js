import View from 'girder/views/View';
import 'girder/utilities/jquery/girderEnable';
import 'girder/utilities/jquery/girderModal';

import PaginateTasksWidget from './PaginateTasksWidget';

import ItemTaskCollection from '../collections/ItemTaskCollection';
import SelectSingleFileTaskWidgetTemplate from '../templates/selectSingleFileTaskWidget.pug';
import SelectSingleFileTaskWidgetSelectedTemplate from '../templates/selectSingleFileTaskWidgetSelected.pug';
import '../stylesheets/selectTaskWidget.styl';

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
            minFileInputs: 1,
            maxFileInputs: 1
        });
    },

    render: function () {
        this.$el
            .html(SelectSingleFileTaskWidgetTemplate({
                item: this.item
            }))
            .girderModal(this);

        this.paginateTasksWidget.setElement(this.$('.g-task-list-container')).render();
        this.$('.g-submit-select-task').girderEnable(false);

        return this;
    },

    _pickTask: function (params) {
        this.task = params.task;
        this.$('.g-submit-select-task').girderEnable(true);

        this.$('.g-task-selected-container').html(SelectSingleFileTaskWidgetSelectedTemplate({
            task: this.task
        }));
    }
});

export default SelectSingleFileTaskWidget;
