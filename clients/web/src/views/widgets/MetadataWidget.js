/**
 * This widget shows a list of metadata in a given item.
 */
girder.views.MetadataWidget = girder.View.extend({
    events: {
        'click .g-add-json-metadata': function (event) {
            this.addMetadata(event, true);
        },
        'click .g-add-simple-metadata': 'addMetadata',
        'click .g-widget-metadata-edit-button': 'editMetadata'
    },

    addMetadata: function (event, json) {
        var EditWidget = (json) ? girder.views.JsonMetadatumEditWidget : girder.views.MetadatumEditWidget;
        var newRow = $('<div>').attr({
            class: 'g-widget-metadata-row editing'
        }).appendTo(this.$el.find('.g-widget-metadata-container'));
        this.metadatumEditWidget = new EditWidget({
            el: newRow,
            item: this.item,
            key: '',
            value: '',
            newDatum: true,
            accessLevel: this.accessLevel,
            parentView: this
        });
    },

    editMetadata: function (event) {
        var row = $(event.currentTarget.parentElement);
        row.addClass('editing').empty();

        var opts = {
            el: row,
            item: this.item,
            key: row.attr('g-key'),
            value: row.attr('g-value'),
            accessLevel: this.accessLevel,
            newDatum: false,
            parentView: this
        };

        if (row.attr('g-is-json') === 'true') {
            opts.value = JSON.parse(row.attr('g-value'));
            this.metadatumEditWidget = new girder.views.JsonMetadatumEditWidget(opts);
        } else {
            this.metadatumEditWidget = new girder.views.MetadatumEditWidget(opts);
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

    render: function () {
        var metaDict = this.item.attributes.meta || {};
        var metaKeys = Object.keys(metaDict);
        metaKeys.sort(girder.localeSort);
        var metaList = [];
        for (var i = 0; i < metaKeys.length; i += 1) {
            var value = metaDict[metaKeys[i]];
            var isJson = false;

            if (typeof value === 'object') {
                value = JSON.stringify(value, null, 4);
                isJson = true;
            }
            metaList.push({key: metaKeys[i], value: value, isJson: isJson});
        }
        this.$el.html(girder.templates.metadataWidget({
            item: this.item,
            meta: metaList,
            accessLevel: this.accessLevel,
            girder: girder
        }));

        this.$('.g-widget-metadata-add-button').tooltip({
            container: this.$el,
            placement: 'left',
            animation: false,
            delay: {show: 100}
        });

        return this;
    },

    setItem: function (item) {
        this.item = item;
        return this;
    }
});

/**
 * This widget enables editing a metadatum
 */
girder.views.MetadatumEditWidget = girder.View.extend({
    events: {
        'click .g-widget-metadata-cancel-button': 'cancelEdit',
        'click .g-widget-metadata-save-button': 'save',
        'click .g-widget-metadata-delete-button': 'deleteMetadatum'
    },

    editTemplate: girder.templates.metadatumEditWidget,

    /* The following 2 functions could be the beginning of
     warranting another layer of abstraction. Particularly
     a MetadatumWidget, and a JsonMetadatumWidget.
     Right now it's a bit odd that the edit widget knows things
     about how to display it in a non-editing environment.  */
    displayValue: function () {
        return this.value;
    },

    viewHtml: function () {
        return girder.templates.metadatumView({
            key: this.key,
            value: this.displayValue(),
            accessLevel: this.accessLevel,
            isJson: false,
            girder: girder
        });
    },

    deleteMetadatum: function (event) {
        event.stopImmediatePropagation();
        var metadataList = $(event.currentTarget.parentElement);
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
        var curRow = $(event.currentTarget.parentElement);
        if (this.newDatum) {
            curRow.remove();
        } else {
            curRow.removeClass('editing').html(this.viewHtml());
        }
    },

    save: function (event, value) {
        event.stopImmediatePropagation();
        var curRow = $(event.currentTarget.parentElement),
            tempKey = curRow.find('.g-widget-metadata-key-input').val(),
            tempValue = value || curRow.find('.g-widget-metadata-value-input').val();

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
            curRow.removeClass('editing').attr({
                'g-key': this.key,
                'g-value': this.displayValue(),
                'g-is-json': typeof value === 'object'
            }).html(this.viewHtml());
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

    initialize: function (settings) {
        this.item = settings.item;
        this.key = settings.key || '';
        this.value = settings.value || '';
        this.accessLevel = settings.accessLevel;
        this.newDatum = settings.newDatum;
        this.render();
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

/**
 * This widget enables editing a Json metadatum
 */
girder.views.JsonMetadatumEditWidget = girder.views.MetadatumEditWidget.extend({
    editTemplate: girder.templates.jsonMetadatumEditWidget,

    displayValue: function () {
        return JSON.stringify(this.value, null, 4);
    },

    deleteMetadatum: function (event) {
        girder.views.MetadatumEditWidget.prototype.deleteMetadatum.apply(this, [event]);
    },

    cancelEdit: function (event) {
        girder.views.MetadatumEditWidget.prototype.cancelEdit.apply(this, [event]);
    },

    save: function (event) {
        try {
            girder.views.MetadatumEditWidget.prototype.save.apply(
                this, [event, this.editor.get()]);
        } catch (err) {
            alert(err);
        }
    },

    viewHtml: function () {
        return girder.templates.metadatumView({
            key: this.key,
            value: this.displayValue(),
            accessLevel: this.accessLevel,
            isJson: true,
            girder: girder
        });
    },

    render: function () {
        girder.views.MetadatumEditWidget.prototype.render.apply(this, arguments);

        this.editor = new JSONEditor(this.$el.find('#json-editor')[0], {
            mode: 'tree',
            modes: ['code', 'tree'],
            error: function (err) {
                alert(err);
                // This will need to be fleshed out to warn the user in a more friendly manner,
                // and possibly give them the option here to 'convert' to a simple edit widget
            }});

            if (this.value) {
                this.editor.set(this.value);
                this.editor.expandAll();
            }

            return this;
        }
    });
