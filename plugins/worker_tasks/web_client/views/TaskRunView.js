import WidgetModel from 'girder_plugins/slicer_cli_web/models/WidgetModel';
import WidgetCollection from 'girder_plugins/slicer_cli_web/collections/WidgetCollection';
import ControlsPanel from 'girder_plugins/slicer_cli_web/views/ControlsPanel';
import View from 'girder/views/View';
import { renderMarkdown } from 'girder/misc';

import template from '../templates/taskRun.pug';
import '../stylesheets/taskRun.styl';

const TaskRunView = View.extend({
    initialize: function () {
        this._taskSpec = this.model.get('meta').workerTaskSpec || {};
        this._inputs = this._taskSpec.inputs || [];
        this._outputs = this._taskSpec.outputs || [];
        this._inputWidgets = new WidgetCollection();
        this._outputWidgets = new WidgetCollection();

        // Build all the widget models from the task IO spec
        this._inputWidgets.add(this._inputs.map((input) => {
            return new WidgetModel({
                type: input.type,
                title: input.name || input.id

            });
        }));
        this._outputWidgets.add(this._outputs.map((output) => {
            return new WidgetModel({
                type: output.type,
                title: output.name || output.id
            });
        }));

        this._inputsPanel = new ControlsPanel({
            title: 'Configure inputs',
            collection: this._inputWidgets,
            parentView: this
        });

        this._outputsPanel = new ControlsPanel({
            title: 'Configure outputs',
            collection: this._outputWidgets,
            parentView: this
        });
    },

    render: function () {
        this.$el.html(template({
            item: this.model,
            renderMarkdown: renderMarkdown
        }));

        if (this._inputs.length) {
            this._inputsPanel.setElement(this.$('.g-inputs-container')).render();
        }

        if (this._outputs.length) {
            this._outputsPanel.setElement(this.$('.g-outputs-container')).render();
        }
    }
});

export default TaskRunView;
