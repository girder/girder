/**
 * This widget shows a list of metadata in a given item.
 */
girder.views.MetadataWidget = girder.View.extend({
    events: {
        'click .g-add-json-metadata': function (event) {
            this.addMetadata(event, 'json');
        },
        'click .g-add-simple-metadata': function (event) {
            this.addMetadata(event, 'simple');
        }
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;
        this.item.on('g:changed', function () {
            this.render();
        }, this);
        this.render();
    },

    modes: {
        simple: {
            editor: function (args) {
                return new girder.views.MetadatumEditWidget(args);
            },
            displayValue: function () {
                return this.value;
            },
            template: girder.templates.metadatumView
        },
        json: {
            editor: function (args) {
                if (args.value !== undefined) {
                    args.value = JSON.parse(args.value);
                }
                return new girder.views.JsonMetadatumEditWidget(args);
            },
            displayValue: function () {
                return JSON.stringify(this.value, null, 4);
            },
            validation: {
                from: {
                    simple: [
                        function (value) {
                            try {
                                JSON.parse(value);
                                return true;
                            } catch (e) {}

                            return false;
                        },
                        'The simple field is not valid JSON and can not be converted.'
                    ]
                }
            },
            template: girder.templates.jsonMetadatumView
        }
    },

    setItem: function (item) {
        this.item = item;
        return this;
    },

    // Does not support modal editing
    getModeFromValue: function (value) {
        return _.isString(value) ? 'simple' : 'json';
    },

    addMetadata: function (event, mode) {
        var EditWidget = this.modes[mode].editor;
        var newRow = $('<div>').attr({
            class: 'g-widget-metadata-row editing'
        }).appendTo(this.$el.find('.g-widget-metadata-container'));
        var value = (mode === 'json') ? '{}' : '';

        var widget = new girder.views.MetadatumWidget({
            el: newRow,
            mode: mode,
            key: '',
            value: value,
            item: this.item,
            accessLevel: this.accessLevel,
            girder: girder,
            parentView: this
        });

        var newEditRow = widget.$el.append('<div></div>');

        new EditWidget({
            el: newEditRow.find('div'),
            item: this.item,
            key: '',
            value: value,
            accessLevel: this.accessLevel,
            newDatum: true,
            parentView: widget
        }).render();
    },

    render: function () {
        var metaDict = this.item.attributes.meta || {};
        var metaKeys = Object.keys(metaDict);
        metaKeys.sort(girder.localeSort);

        // Metadata header
        this.$el.html(girder.templates.metadataWidget({
            item: this.item,
            accessLevel: this.accessLevel,
            girder: girder
        }));

        // Append each metadatum
        _.each(metaKeys, function (metaKey) {
            this.$el.find('.g-widget-metadata-container').append(new girder.views.MetadatumWidget({
                mode: this.getModeFromValue(metaDict[metaKey]),
                key: metaKey,
                value: metaDict[metaKey],
                accessLevel: this.accessLevel,
                girder: girder,
                parentView: this
            }).render().$el);
        }, this);

        this.$('.g-widget-metadata-add-button').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }
});

girder.views.MetadatumWidget = girder.View.extend({
    events: {
        'click .g-widget-metadata-edit-button': 'editMetadata'
    },

    initialize: function (settings) {
        if (!_.has(this.parentView.modes, settings.mode)) {
            throw 'Unsupported metadatum mode ' + settings.mode + ' detected.';
        }

        this.mode = settings.mode;
        this.key = settings.key;
        this.value = settings.value;
        this.accessLevel = settings.accessLevel;
        this.parentView = settings.parentView;
    },

    _validate: function (from, to, value) {
        var newMode = this.parentView.modes[to];

        if (_.has(newMode, 'validation') &&
            _.has(newMode.validation, 'from') &&
            _.has(newMode.validation.from, from)) {
            var validate = newMode.validation.from[from][0];
            var msg = newMode.validation.from[from][1];

            if (!validate(value)) {
                girder.events.trigger('g:alert', {
                    text: msg,
                    type: 'warning'
                });
                return false;
            }
        }

        return true;
    },

    // @todo too much duplication with editMetadata
    toggleEditor: function (event, newEditorMode, existingEditor, overrides) {
        var fromEditorMode =
                (existingEditor instanceof girder.views.JsonMetadatumEditWidget)
                    ? 'json' : 'simple';
        var newValue = (overrides || {}).value || existingEditor.$el.attr('g-value');
        if (!this._validate(fromEditorMode, newEditorMode, newValue)) {
            return;
        }

        var row = existingEditor.$el;
        existingEditor.destroy();
        row.addClass('editing').empty();

        var opts = _.extend({
            el: row,
            item: this.parentView.item,
            key: row.attr('g-key'),
            value: row.attr('g-value'),
            accessLevel: this.accessLevel,
            newDatum: false,
            parentView: this
        }, (overrides || {}));

        this.parentView.modes[newEditorMode].editor(opts).render();
    },

    editMetadata: function (event) {
        var row = $(event.currentTarget.parentElement);
        row.addClass('editing').empty();

        var newEditRow = row.append('<div></div>');

        var opts = {
            el: newEditRow.find('div'),
            item: this.parentView.item,
            key: row.attr('g-key'),
            value: row.attr('g-value'),
            accessLevel: this.accessLevel,
            newDatum: false,
            parentView: this
        };

        // If they're trying to open false, null, 6, etc which are not stored as strings
        if (this.mode === 'json') {
            try {
                var jsonValue = JSON.parse(row.attr('g-value'));

                if (jsonValue !== undefined && !_.isObject(jsonValue)) {
                    opts.value = jsonValue;
                }
            } catch (e) {}
        }

        this.parentView.modes[this.mode].editor(opts).render();
    },

    render: function () {
        this.$el.attr({
            class: 'g-widget-metadata-row',
            'g-key': this.key,
            'g-value': _.bind(this.parentView.modes[this.mode].displayValue, this)()
        }).empty();

        this.$el.html(this.parentView.modes[this.mode].template({
            key: this.key,
            value: _.bind(this.parentView.modes[this.mode].displayValue, this)(),
            accessLevel: this.accessLevel,
            girder: girder
        }));

        return this;
    }
});

girder.views.MetadatumEditWidget = girder.View.extend({
    events: {
        'click .g-widget-metadata-cancel-button': 'cancelEdit',
        'click .g-widget-metadata-save-button': 'save',
        'click .g-widget-metadata-delete-button': 'deleteMetadatum',
        'click .g-widget-metadata-toggle-button': function (event) {
            var editorType;
            // @todo modal
            // in the future this event will have the new editorType (assuming a dropdown)
            if (this instanceof girder.views.JsonMetadatumEditWidget) {
                editorType = 'simple';
            } else {
                editorType = 'json';
            }

            this.parentView.toggleEditor(event, editorType, this, {
                // Save state before toggling editor
                key: this.$el.find('.g-widget-metadata-key-input').val(),
                value: this.getCurrentValue()
            });
        }
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.key = settings.key || '';
        this.value = (settings.value !== undefined) ? settings.value : '';
        this.accessLevel = settings.accessLevel;
        this.newDatum = settings.newDatum;
    },

    editTemplate: girder.templates.metadatumEditWidget,

    getCurrentValue: function () {
        return this.$el.find('.g-widget-metadata-value-input').val();
    },

    deleteMetadatum: function (event) {
        event.stopImmediatePropagation();
        var metadataList = $(event.currentTarget.parentElement).parent();
        var params = {
            text: 'Are you sure you want to delete the metadatum <b>' +
                _.escape(this.key) + '</b>?',
            escapedHtml: true,
            yesText: 'Delete',
            confirmCallback: _.bind(function () {
                this.item.removeMetadata(this.key, function () {
                    metadataList.remove();
                });
            }, this)
        };
        girder.confirm(params);
    },

    cancelEdit: function (event) {
        event.stopImmediatePropagation();
        var curRow = $(event.currentTarget.parentElement).parent();
        if (this.newDatum) {
            curRow.remove();
        } else {
            this.parentView.render();
        }
    },

    save: function (event, value) {
        event.stopImmediatePropagation();
        var curRow = $(event.currentTarget.parentElement),
            tempKey = curRow.find('.g-widget-metadata-key-input').val(),
            tempValue = (value !== undefined) ? value : curRow.find('.g-widget-metadata-value-input').val();

        if (this.newDatum && tempKey === '') {
            girder.events.trigger('g:alert', {
                text: 'A key is required for all metadata.',
                type: 'warning'
            });
            return;
        }

        var saveCallback = _.bind(function () {
            this.key = tempKey;
            this.value = tempValue;

            this.parentView.key = this.key;
            this.parentView.value = this.value;

            if (this instanceof girder.views.JsonMetadatumEditWidget) {
                this.parentView.mode = 'json';
            } else {
                this.parentView.mode = 'simple';
            }

            this.parentView.render();

            this.newDatum = false;
        }, this);

        var errorCallback = function (out) {
            girder.events.trigger('g:alert', {
                text: out.message,
                type: 'danger'
            });
        };

        if (this.newDatum) {
            this.item.addMetadata(tempKey, tempValue, saveCallback, errorCallback);
        } else {
            this.item.editMetadata(tempKey, this.key, tempValue, saveCallback, errorCallback);
        }
    },

    render: function () {
        this.$el.html(this.editTemplate({
            item: this.item,
            key: this.key,
            value: this.value,
            accessLevel: this.accessLevel,
            newDatum: this.newDatum,
            girder: girder
        }));
        this.$el.find('.g-widget-metadata-key-input').focus();

        this.$('[title]').tooltip({
            container: this.$el,
            placement: 'bottom',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }

});

girder.views.JsonMetadatumEditWidget = girder.views.MetadatumEditWidget.extend({
    editTemplate: girder.templates.jsonMetadatumEditWidget,

    getCurrentValue: function () {
        return this.editor.getText();
    },

    save: function (event) {
        try {
            girder.views.MetadatumEditWidget.prototype.save.apply(
                this, [event, this.editor.get()]);
        } catch (err) {
            girder.events.trigger('g:alert', {
                text: 'The field contains invalid JSON and can not be saved.',
                type: 'warning'
            });
        }
    },

    render: function () {
        girder.views.MetadatumEditWidget.prototype.render.apply(this, arguments);

        this.editor = new JSONEditor(this.$el.find('.g-json-editor')[0], {
            mode: 'tree',
            modes: ['code', 'tree'],
            error: function () {
                girder.events.trigger('g:alert', {
                    text: 'The field contains invalid JSON and can not be viewed in Tree Mode.',
                    type: 'warning'
                });
            }
        });

        if (this.value !== undefined) {
            this.editor.setText(JSON.stringify(this.value));
            this.editor.expandAll();
        }

        return this;
    }
});
