import WidgetModel from 'girder_plugins/slicer_cli_web/models/WidgetModel';
import WidgetCollection from 'girder_plugins/slicer_cli_web/collections/WidgetCollection';
import ControlsPanel from 'girder_plugins/slicer_cli_web/views/ControlsPanel';
import View from 'girder/views/View';
import router  from 'girder/router';
import { restRequest } from 'girder/rest';
import { renderMarkdown } from 'girder/misc';

import template from '../templates/taskRun.pug';
import '../stylesheets/taskRun.styl';

const TaskRunView = View.extend({
    events: {
        'click .g-run-task': 'execute'
    },

    initialize: function () {
        this._taskSpec = this.model.get('meta').itemTaskSpec || {};
        this._inputs = this._taskSpec.inputs || [];
        this._outputs = this._taskSpec.outputs || [];
        this._inputWidgets = new WidgetCollection();
        this._outputWidgets = new WidgetCollection();

        // Build all the widget models from the task IO spec
        this._inputWidgets.add(this._inputs.map((input) => {
            return new WidgetModel({
                type: input.type,
                title: input.name || input.id,
                id: input.id || input.name,
                description: input.description || '',
                values: input.values,
                value: input.default
            });
        }));

        this._outputWidgets.add(this._outputs.map((output) => {
            return new WidgetModel({
                type: output.type,
                title: output.name || output.id,
                id: output.id || output.name,
                description: output.description || ''
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
        var hasInputs = !!this._inputs.length,
            hasOutputs = !!this._outputs.length;

        this.$el.html(template({
            item: this.model,
            hasInputs: hasInputs,
            hasOutputs: hasOutputs,
            renderMarkdown: renderMarkdown
        }));

        if (hasInputs) {
            this._inputsPanel.setElement(this.$('.g-inputs-container')).render();
        }

        if (hasOutputs) {
            this._outputsPanel.setElement(this.$('.g-outputs-container')).render();
        }
    },

    /**
     * Validates that all of the widgets are in a valid state. Displays any
     * invalid states and
     */
    validate: function () {
        let ok = true;
        const test = (model) => {
            if(!model.isValid()) {
               ok = false;
            }
        };

        // Don't short-circuit; we want to highlight *all* invalid inputs
        this._inputWidgets.each(test);
        this._outputWidgets.each(test);

        return ok;
    },

    /**
     * Translates the WidgetCollection state for the input and output widgets into the
     * appropriate girder_worker input and output bindings, then invokes the endpoint
     * to execute the task. TODO We probably want to move that translation layer down into
     * the WidgetCollection itself in the future.
     */
    execute: function (e) {
        if (!this.validate()) {
            this.$('.g-validation-failed-message').text(
                'One or more of your inputs or outputs is invalid, they are highlighted in red.');
            return;
        }
        this.$('.g-validation-failed-message').empty();
        $(e.currentTarget).attr('disabled', 'true').addClass('disabled');

        const inputs = {},
              outputs = {};

        const translate = (model) => {
            const val = model.value();

            switch (model.get('type')) {
                case 'image': // This is an input
                    return {
                        mode: 'girder',
                        resource_type: 'file',
                        id: val.id,
                    };
                case 'file': // This is an input
                    return {
                        mode: 'girder',
                        resource_type: 'item',
                        id: val.id,
                    };
                case 'new-file': // This is an output
                    return {
                        mode: 'girder',
                        parent_id: model.value().get('folderId'),
                        parent_type: 'folder',
                        name: val.name()
                    };
                default:
                    return {
                        mode: 'inline',
                        data: model.value()
                    };
            }
        };

        this._inputWidgets.each((model) => {
            inputs[model.id] = translate(model);
        });
        this._outputWidgets.each((model) => {
            outputs[model.id] = translate(model);
        });

        restRequest({
            path: `item_task/${this.model.id}/execution`,
            type: 'POST',
            data: {
                inputs: JSON.stringify(inputs),
                outputs: JSON.stringify(outputs)
            },
            error: null
        }).done((resp) => {
            router.navigate(`job/${resp._id}`, {trigger: true});
        }).error((resp) => {
            $(e.currentTarget).attr('disabled', null).removeClass('disabled');
            this.$('.g-validation-failed-message').text('Error: ' + resp.responseJSON.message);
        });
    }
});

export default TaskRunView;
