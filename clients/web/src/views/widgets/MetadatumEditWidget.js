/**
 * This widget enables editing a metadatum
 */
girder.views.MetadatumEditWidget = girder.View.extend({
    events: {
        'click .g-item-metadata-cancel-button': 'cancelEdit',
        'click .g-item-metadata-save-button': 'save',
        'click .g-item-metadata-delete-button': 'deleteMetadatum'
    },

    deleteMetadatum: function (event) {
        event.stopImmediatePropagation();
        var metadataList = $(event.currentTarget.parentElement);
        var params = {
            text: 'Are you sure you want to delete the metadatum <b>' +
                  this.key + '</b>?',
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
            curRow.removeClass('editing').html(jade.templates.metadatumView({
                key: this.key,
                value: this.value,
                accessLevel: this.accessLevel,
                girder: girder
            }));
        }
    },

    save: function (event) {
        event.stopImmediatePropagation();
        var curRow = $(event.currentTarget.parentElement),
            tempKey = curRow.find('.g-item-metadata-key-input').val(),
            tempValue = curRow.find('.g-item-metadata-value-input').val();

        if (this.newDatum && tempKey === "") {
            girder.events.trigger('g:alert', {
                'text': 'A key is required for all metadata.',
                'type': 'warning'
            });
            return;
        }

        var saveCallback = _.bind(function () {
            this.key = tempKey;
            this.value = tempValue;
            curRow.removeClass('editing').attr({
                'g-key': this.key,
                'g-value': this.value
            }).html(jade.templates.metadatumView({
                key: this.key,
                value: this.value,
                accessLevel: this.accessLevel,
                girder: girder
            }));
            this.newDatum = false;
        }, this);

        var errorCallback = function (out) {
            girder.events.trigger('g:alert', {
                'text': out.message,
                'type': 'danger'
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
        this.$el.html(jade.templates.metadatumEditWidget({
            item: this.item,
            key: this.key,
            value: this.value,
            accessLevel: this.accessLevel,
            newDatum: this.newDatum,
            girder: girder
        }));
        this.$el.find('.g-item-metadata-key-input').focus();

        this.$('[title]').tooltip({
            container: this.$el,
            placement: 'bottom',
            animation: false,
            delay: {show: 100}
        });

        return this;
    }

});
