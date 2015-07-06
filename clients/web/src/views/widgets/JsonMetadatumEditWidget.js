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
