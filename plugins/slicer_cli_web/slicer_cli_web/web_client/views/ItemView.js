import WidgetCollection from '../collections/WidgetCollection';
import ControlsPanel from './ControlsPanel';
import PanelGroup from './PanelGroup';
import { parse } from '../parser';
import slicerUI from '../templates/slicerUI.pug';
import '../stylesheets/slicerUI.styl';
import { showJobSuccessAlert } from './utils';
import utils from '../utils';

const $ = girder.$;
const _ = girder._;
const View = girder.views.View;
const {wrap} = girder.utilities.PluginUtils;
const {restRequest} = girder.rest;
const ItemView = girder.views.body.ItemView;

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.model.get('meta').slicerCLIType !== 'task') {
            return;
        }
        this.slicerCLIPanel = new SlicerUI({
            el: $('<div>', { class: 'g-item-slicer-ui' })
                .insertAfter(this.$('.g-item-info')),
            parentView: this,
            taskModel: this.model
        });
        this.slicerCLIPanel.render();
    });
    return render.call(this);
});

const SlicerUI = View.extend({
    events: {
        'click .s-info-panel-submit': 'submit'
    },
    initialize(settings) {
        this.panels = [];
        this._panelViews = {};

        this.taskModel = settings.taskModel;

        this.loadModel();
    },

    render() {
        this.$el.html(slicerUI({
            panels: this.panels
        }));
        this.panels.forEach((panel) => {
            this._panelViews[panel.id] = new ControlsPanel({
                controlWidget: {
                    disableRegionSelect: true,
                    setDefaultOutput: this.taskModel.get('name'),
                    rootPath: false
                },
                parentView: this,
                collection: new WidgetCollection(panel.parameters),
                title: panel.label,
                description: panel.description,
                advanced: panel.advanced,
                el: this.$el.find(`#${panel.id}`)
            });
            this._panelViews[panel.id].render();
        });
        if (this.$el.find('.has-datalist')) {
            utils.handleDatalist(this.$el, `slicer_cli_web/cli/${this.taskModel.id}`, () => this.generateParameters());
        }
        return this;
    },

    loadModel() {
        const xml = this.taskModel.get('meta').xml;
        const opts = {};
        this.spec = parse(xml, opts);

        if (opts.output) {
            this._addParamFileOutput();
        }

        // Create a panel for each "group" in the schema, and copy
        // the advanced property from the parent panel.
        this.panels = [].concat(...this.spec.panels.map((panel) => {
            return panel.groups.map((group) => {
                group.advanced = !!panel.advanced;
                group.id = _.uniqueId('panel-');
                return group;
            });
        }));
    },

    _addParamFileOutput() {
        this.spec.panels.unshift({
            groups: [{
                label: 'Parameter outputs',
                parameters: [{
                    type: 'new-file',
                    slicerType: 'file',
                    id: 'returnparameterfile',
                    title: 'Parameter output file',
                    description: 'Output parameters returned by the analysis will be stored in this file.',
                    channel: 'output'
                }]
            }]
        });
    },

    generateParameters() {
        return PanelGroup.prototype.parameters.call(this);
    },

    validate() {
        const invalidModels = PanelGroup.prototype.models.call(this, undefined, (m) => {
            return !m.isValid();
        });
        const alert = this.$('.s-validation-alert');
        alert.toggleClass('hidden', invalidModels.length === 0);
        alert.text(`Validation errors occurred for: ${invalidModels.map((d) => d.get('title')).join(', ')}`);

        return invalidModels.length === 0;
    },

    submit() {
        if (!this.validate()) {
            return;
        }
        const params = this.generateParameters();
        _.each(params, (value, key) => {
            if (Array.isArray(value)) {
                params[key] = JSON.stringify(value);
            }
        });

        // post the job to the server
        restRequest({
            url: `slicer_cli_web/cli/${this.taskModel.id}/run`,
            method: 'POST',
            data: params
        }).then((data) => {
            showJobSuccessAlert(data);
            return null;
        });
    }

});
