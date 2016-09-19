slicer.views.PanelGroup = girder.View.extend({
    events: {
        'click .s-info-panel-reload': 'reload',
        'click .s-info-panel-submit': 'submit',
        'click .s-remove-panel': 'removePanel'
    },
    initialize: function () {
        this.panels = [];
        this._panelViews = {};

        this._jobsPanelView = new slicer.views.JobsPanel({
            parentView: this,
            spec: {
                title: 'Jobs',
                collapsed: true
            }
        });

        this.listenTo(slicer.events, 'query:analysis', this.schema);
    },
    render: function () {
        this.$el.html(slicer.templates.panelGroup({
            info: this._gui,
            panels: this.panels
        }));
        this.$el.addClass('hidden');
        _.each(this._panelViews, function (view) {
            view.remove();
        });
        this._panelViews = {};
        this._jobsPanelView.setElement(this.$('.s-jobs-panel')).render();
        _.each(this.panels, _.bind(function (panel) {
            this.$el.removeClass('hidden');
            this._panelViews[panel.id] = new slicer.views.ControlsPanel({
                parentView: this,
                collection: new slicer.collections.Widget(panel.parameters),
                title: panel.label,
                advanced: panel.advanced,
                el: this.$el.find('#' + panel.id)
            });

            this._panelViews[panel.id].render();
        }, this));
    },

    /**
     * Submit the current values to the server at the given endpoint.
     */
    submit: function (endpoint) {
        var params, invalid = false;

        invalid = this.invalidModels();

        if (invalid.length) {
            girder.events.trigger('g:alert', {
                icon: 'attention',
                text: 'Please enter a valid value for: ' + invalid.map(function (m) {return m.get('title');}).join(', '),
                type: 'danger'
            });
            return;
        }

        params = this.parameters();
        _.each(params, function (value, key) {
            if (_.isArray(value)) {
                params[key] = JSON.stringify(value);
            }
        });

        // post the job to the server
        girder.restRequest({
            path: endpoint,
            type: 'POST',
            data: params
        }).then(function (data) {
            slicer.events.trigger('h:submit', data);
        });
    },

    /**
     * Get the current values of all of the parameters contained in the gui.
     * Returns an object that maps each parameter id to it's value.
     */
    parameters: function () {
        return _.chain(this._panelViews)
            .pluck('collection')
            .invoke('values')
            .reduce(function (a, b) {
                return _.extend(a, b);
            }, {})
            .value();
    },

    /**
     * Return an array of all widget models optionally filtered by the given panel id
     * and model filtering function.
     */
    models: function (panelId, modelFilter) {
        modelFilter = modelFilter || function () { return true; };
        return _.chain(this._panelViews)
            .filter(function (v, i) {
                return panelId === undefined || panelId === i;
            })
            .pluck('collection')
            .pluck('models')
            .flatten()
            .filter(modelFilter)
            .value();
    },

    /**
     * Return an array of all invalid models.  Optionally filter by the given panel id.
     */
    invalidModels: function (panelId) {
        return this.models(panelId, function (m) { return !m.isValid(); });
    },

    /**
     * Return true if all parameters are set and valid.  Also triggers 'invalid'
     * events on each of the invalid models as a byproduct.
     */
    validate: function () {
        return !this.invalidModels().length;
    },

    /**
     * Remove a panel after confirmation from the user.
     */
    removePanel: function (e) {
        girder.confirm({
            text: 'Are you sure you want to remove this panel?',
            confirmCallback: _.bind(function () {
                var el = $(e.currentTarget).data('target');
                var id = $(el).attr('id');
                this.panels = _.filter(this.panels, function (panel) {
                    return panel.id !== id;
                });
                this.render();
            }, this)
        });
    },

    /**
     * Remove all panels.
     */
    reset: function () {
        this.panels = [];
        this._gui = null;
        this.render();
    },

    /**
     * Restore all panels to the default state.
     */
    reload: function () {
        if (!this._gui) {
            return this;
        }

        // Create a panel for each "group" in the schema, and copy
        // the advanced property from the parent panel.
        this.panels = _.chain(this._gui.panels).map(function (panel) {
            return _.map(panel.groups, function (group) {
                group.advanced = !!panel.advanced;
                group.id = _.uniqueId('panel-');
                return group;
            });
        }).flatten(true).value();

        this.render();
        return this;
    },

    /**
     * Generate panels from a slicer XML schema.
     */
    schema: function (xml) {
        var fail = false;

        // clear the view on null
        if (xml === null) {
            return this.reset();
        }

        try {
            this.json(slicer.schema.parse(xml));
        } catch (e) {
            fail = true;
        }

        if (fail) {
            girder.events.trigger('g:alert', {
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
    json: function (spec) {
        if (_.isString(spec)) {
            spec = JSON.parse(spec);
        }
        this._gui = spec;
        this.reload();
        return this;
    }
});
