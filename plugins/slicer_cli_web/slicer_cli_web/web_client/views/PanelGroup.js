import { parse } from '../parser';
import WidgetCollection from '../collections/WidgetCollection';
import events from '../events';
import JobsPanel from './JobsPanel';
import ControlsPanel from './ControlsPanel';
import utils from '../utils';

import panelGroup from '../templates/panelGroup.pug';
import '../stylesheets/panelGroup.styl';

const $ = girder.$;
const _ = girder._;
const View = girder.views.View;
const girderEvents = girder.events;
const restRequest = girder.rest.restRequest;
const confirm = girder.dialog.confirm;

const PanelGroup = View.extend({
    events: {
        'click .s-info-panel-reload': 'reload',
        'click .s-info-panel-submit': 'submit',
        'click .s-remove-panel': 'removePanel'
    },
    initialize(settings) {
        this.panels = [];
        this._panelViews = {};
        this._closeButton = (settings || {}).closeButton;

        this._jobsPanelView = new JobsPanel({
            parentView: this,
            spec: {
                title: 'Jobs',
                collapsed: true
            }
        });

        this.listenTo(events, 'query:analysis', (path, query) => this.setAnalysis(path));
    },
    render() {
        this.$el.html(panelGroup({
            info: this._gui,
            panels: this.panels,
            closeButton: this._closeButton
        }));
        this.$el.addClass('hidden');
        _.each(this._panelViews, function (view) {
            view.remove();
        });
        this._panelViews = {};
        this._jobsPanelView.setElement(this.$('.s-jobs-panel')).render();
        _.each(this.panels, (panel) => {
            this.$el.removeClass('hidden');
            this._panelViews[panel.id] = new ControlsPanel({
                parentView: this,
                collection: new WidgetCollection(panel.parameters),
                title: panel.label,
                advanced: panel.advanced,
                el: this.$el.find('#' + panel.id)
            });

            this._panelViews[panel.id].render();
        });

        events.trigger('h:analysis:rendered', this);
        if (!this.$el.hasClass('hidden') && this.$el.find('.has-datalist')) {
            utils.handleDatalist(this.$el, this._basePath, () => this.parameters());
        }
        return this;
    },

    /**
     * Submit the current values to the server.
     */
    submit() {
        const invalid = this.invalidModels();

        if (invalid.length > 0) {
            girderEvents.trigger('g:alert', {
                icon: 'attention',
                text: 'Please enter a valid value for: ' + invalid.map((m) => m.get('title')).join(', '),
                type: 'danger'
            });
            return;
        }

        const params = this.parameters();
        _.each(params, function (value, key) {
            if (Array.isArray(value)) {
                params[key] = JSON.stringify(value);
            }
            const ctlmatch = value ? ('' + value).match(/^{#control:(.*)#}$/) : undefined;
            if (ctlmatch) {
                params[key] = $(ctlmatch[1]).val() || $(ctlmatch[1]).text() || $(ctlmatch[1]).prop('checked');
            }
        });

        // post the job to the server
        restRequest({
            url: this._submit,
            method: 'POST',
            data: params
        }).then((data) => {
            events.trigger('h:submit', data);
            return null;
        });
    },

    /**
     * Get the current values of all of the parameters contained in the gui.
     * Returns an object that maps each parameter id to it's value.
     */
    parameters() {
        return _.chain(this._panelViews)
            .pluck('collection')
            .invoke('values')
            .reduce((a, b) => _.extend(a, b), {})
            .value();
    },

    /**
     * Return an array of all widget models optionally filtered by the given panel id
     * and model filtering function.
     */
    models(panelId, modelFilter) {
        modelFilter = modelFilter || _.constant(true);
        return _.chain(this._panelViews)
            .filter((_, i) => panelId === undefined || panelId === i)
            .pluck('collection')
            .pluck('models')
            .flatten()
            .filter(modelFilter)
            .value();
    },

    /**
     * Return an array of all invalid models.  Optionally filter by the given panel id.
     */
    invalidModels(panelId) {
        return this.models(panelId, (m) => !m.isValid());
    },

    /**
     * Return true if all parameters are set and valid.  Also triggers 'invalid'
     * events on each of the invalid models as a byproduct.
     */
    validate() {
        return !this.invalidModels().length;
    },

    /**
     * Remove a panel after confirmation from the user.
     */
    removePanel(e) {
        confirm({
            text: 'Are you sure you want to remove this panel?',
            confirmCallback: () => {
                const el = $(e.currentTarget).data('target');
                const id = $(el).attr('id');
                this.panels = _.reject(this.panels, _.matcher({id: id}));
                this.render();
            }
        });
    },

    /**
     * Remove all panels.
     */
    reset() {
        this.panels = [];
        this._gui = null;
        this._submit = null;
        this.render();
    },

    /**
     * Restore all panels to the default state.
     */
    reload() {
        if (!this._gui) {
            return this;
        }

        // Create a panel for each "group" in the schema, and copy
        // the advanced property from the parent panel.
        this.panels = _.chain(this._gui.panels).map((panel) => {
            return panel.groups.map((group) => {
                group.advanced = !!panel.advanced;
                group.id = _.uniqueId('panel-');
                return group;
            });
        }).flatten(true).value();

        this.render();
        return this;
    },

    /**
     * Set the panel group according to the given schema path.
     * This should be a url fragment such as
     *
     *   path = `/slicer_cli_web/cli/<id>`
     *
     * This code will fetch the actual schema from `path + '/xml'`
     * and cause submissions to post to `path + '/run'`.
     */
    setAnalysis(path, xml) {
        if (!path) {
            this.reset();
            return $.when();
        }
        const process = (xml) => {
            this._submit = `${path}/run`;
            this._basePath = path;
            this._schema(xml);
            events.trigger('h:analysis', path, xml);
        };
        if (xml) {
            return process(xml);
        }
        return restRequest({
            url: path + '/xml',
            dataType: 'xml'
        }).then(process);
    },

    /**
     * Generate panels from a slicer XML schema.
     */
    _schema(xml) {
        let fail = false;
        const opts = {};

        // clear the view on null
        if (xml === null) {
            return this.reset();
        }

        try {
            const json = parse(xml, opts);
            this._json(json, opts.output);
        } catch (e) {
            fail = true;
        }

        if (fail) {
            girderEvents.trigger('g:alert', {
                icon: 'attention',
                text: 'Invalid XML schema',
                type: 'danger'
            });
            this.reset();
            return this;
        }

        return this;
    },

    /**
     * Generate panels from a json schema.
     */
    _json(spec, outputs) {
        if (_.isString(spec)) {
            spec = JSON.parse(spec);
        }
        this._gui = spec;
        if (outputs) {
            this._addParamFileOutput();
        }
        this.reload();
        return this;
    },

    /**
     * Add an output file for storing parameter outputs.
     */
    _addParamFileOutput() {
        this._gui.panels.unshift({
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
    }
});

export default PanelGroup;
