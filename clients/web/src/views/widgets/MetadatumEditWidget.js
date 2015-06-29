/**
 * This widget enables editing a metadatum
 */
girder.views.MetadatumEditWidget = girder.View.extend({
    events: {
        'click .g-widget-metadata-cancel-button': 'cancelEdit',
        'click .g-widget-metadata-save-button': 'save',
        'click .g-widget-metadata-delete-button': 'deleteMetadatum'
    },

    isJsonValue: function (s) {
        s = s || this.value;

        try {
            var jsonValue = JSON.parse(s);

            if (jsonValue && typeof jsonValue === 'object' && jsonValue !== null) {
                return jsonValue;
            }
        } catch (err) {}

        return false;
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
            curRow.removeClass('editing').html(girder.templates.metadatumView({
                key: this.key,
                value: this.value,
                isJson: this.isJsonValue(),
                accessLevel: this.accessLevel,
                girder: girder
            }));
        }
    },

    save: function (event) {
        event.stopImmediatePropagation();
        var curRow = $(event.currentTarget.parentElement),
            tempKey = curRow.find('.g-widget-metadata-key-input').val();

        // If it's json and we have an active editor, we need to retrieve that JSON
        if (this.isJsonValue() && this.editor) {
            var tempValue = this.editor.getText();
        } else {
            var tempValue = curRow.find('.g-widget-metadata-value-input').val();
        }

        if (this.newDatum && tempKey === '') {
            girder.events.trigger('g:alert', {
                text: 'A key is required for all metadata.',
                type: 'warning'
            });
            return;
        }

        var displayValue = tempValue;
        var jsonValue = this.isJsonValue(tempValue);

        if (jsonValue) {
            tempValue = jsonValue;
        }

        var saveCallback = _.bind(function () {
            this.key = tempKey;
            this.value = displayValue;
            curRow.removeClass('editing').attr({
                'g-key': this.key,
                'g-value': this.value
            }).html(girder.templates.metadatumView({
                key: this.key,
                value: (jsonValue) ? JSON.stringify(jsonValue, null, 4) : this.value,
                isJson: this.isJsonValue(),
                accessLevel: this.accessLevel,
                girder: girder
            }));
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
        var jsonValue = this.isJsonValue();

        this.$el.html(girder.templates.metadatumEditWidget({
            item: this.item,
            key: this.key,
            value: this.value,
            isJson: jsonValue,
            accessLevel: this.accessLevel,
            newDatum: this.newDatum,
            girder: girder
        }));
        this.$el.find('.g-widget-metadata-key-input').focus();

        if (jsonValue) {
            var options = {
                mode: 'tree',
                modes: ['code', 'text', 'tree'],
                error: function (err) { alert(err.toString()); }
            };

            this.editor = new JSONEditor(this.$el.find('.json-editor')[0], options, jsonValue);
        }

        this.$('[title]').tooltip({
            container: this.$el,
            placement: 'bottom',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }

});
