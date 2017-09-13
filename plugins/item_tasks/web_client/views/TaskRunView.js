import $ from 'jquery';
import _ from 'underscore';

import View from 'girder/views/View';
import FolderModel from 'girder/models/FolderModel';
import ItemModel from 'girder/models/ItemModel';
import router  from 'girder/router';
import { restRequest } from 'girder/rest';
import { renderMarkdown } from 'girder/misc';

import template from '../templates/taskRun.pug';
import '../stylesheets/taskRun.styl';
import WidgetCollection from '../collections/WidgetCollection';

import ControlsPanel from './ControlsPanel';

const TaskRunView = View.extend({
    events: {
        'click .g-run-task': 'execute'
    },

    initialize: function (settings) {
        this.inputWidgets = new WidgetCollection();
        this.outputWidgets = new WidgetCollection();

        const taskSpec = this.model.get('meta').itemTaskSpec || {};
        const inputs = taskSpec.inputs || [];
        const outputs = taskSpec.outputs || [];
        const initialValues = settings.initialValues || null;
        const initialInputs = (initialValues && initialValues.inputs) || {};
        const initialOutputs = (initialValues && initialValues.outputs) || {};

        // Build all the widget models from the task IO spec
        this.inputWidgets.add(
            inputs.map((input) => this._setJobInfo(input, initialInputs))
        );

        this.outputWidgets.add(
            outputs.map((output) => this._setJobInfo(output, initialOutputs))
        );

        this.inputsPanel = new ControlsPanel({
            title: 'Configure inputs',
            collection: this.inputWidgets,
            parentView: this
        });

        this.outputsPanel = new ControlsPanel({
            title: 'Configure outputs',
            collection: this.outputWidgets,
            parentView: this
        });
    },

    /**
     * Fill in values according to an existing job.
     *
     * @param {object} spec The task parameter spec
     * @param {object} bindings The job parameter bindings
     */
    _setJobInfo: function (spec, bindings) {
        const match = bindings[spec.id || spec.name] || {};
        if (match.mode === 'girder' && match.resource_type === 'item') {
            spec.value = new ItemModel({
                _id: match.id,
                _modelType: 'item',
                name: match.fileName || match.id
            });
            spec.fileName = match.fileName || match.id;
        } else if (match.mode === 'girder' && _.contains(['folder', 'collection', 'user'], match.parent_type)) {
            spec.value = new FolderModel({
                _id: match.parent_id,
                _modelType: 'folder'
            });
            spec.fileName = match.name || match.id;
        } else if (_.has(match, 'data')) {
            spec.value = match.data;
        }
        return spec;
    },

    render: function () {
        var hasInputs = !!this.inputWidgets.length,
            hasOutputs = !!this.outputWidgets.length;

        this.$el.html(template({
            item: this.model,
            hasInputs: hasInputs,
            hasOutputs: hasOutputs,
            renderMarkdown: renderMarkdown
        }));

        if (hasInputs) {
            this.inputsPanel.setElement(this.$('.g-inputs-container')).render();
        }

        if (hasOutputs) {
            this.outputsPanel.setElement(this.$('.g-outputs-container')).render();
        }

        return this;
    },

    /**
     * Validates that all of the widgets are in a valid state. Displays any
     * invalid states and
     */
    validate: function () {
        let ok = true;
        const test = (model) => {
            if (!model.isValid()) {
                ok = false;
            }
        };

        // Don't short-circuit; we want to highlight *all* invalid inputs
        this.inputWidgets.each(test);
        this.outputWidgets.each(test);

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
        $(e.currentTarget).girderEnable(false);

        const inputs = {}, outputs = {};

        const translate = (model) => {
            let val = model.value();
            switch (model.get('type')) {
                case 'image':
                case 'file': // This is an input
                    return {
                        mode: 'girder',
                        resource_type: 'item',
                        id: val.id,
                        fileName: model.get('fileName') || null
                    };
                case 'new-file': // This is an output
                    return {
                        mode: 'girder',
                        parent_id: val.id,
                        parent_type: 'folder',
                        name: model.get('fileName')
                    };
                case 'new-folder': // This is an output
                    return {
                        mode: 'girder',
                        parent_id: val.id,
                        parent_type: val.get('_modelType'),
                        name: model.get('fileName')
                    };
                default:
                    if (model.isVector()) {
                        val = val.join(',');
                    }
                    return {
                        mode: 'inline',
                        data: val
                    };
            }
        };

        this.inputWidgets.each((model) => {
            inputs[model.id] = translate(model);
        });
        this.outputWidgets.each((model) => {
            outputs[model.id] = translate(model);
        });

        restRequest({
            url: `item_task/${this.model.id}/execution`,
            method: 'POST',
            data: {
                inputs: JSON.stringify(inputs),
                outputs: JSON.stringify(outputs)
            },
            error: null
        }).done((resp) => {
            router.navigate(`job/${resp._id}`, {trigger: true});
        }).fail((resp) => {
            $(e.currentTarget).girderEnable(true);
            this.$('.g-validation-failed-message').text('Error: ' + resp.responseJSON.message);
        });
    }
});

export default TaskRunView;
