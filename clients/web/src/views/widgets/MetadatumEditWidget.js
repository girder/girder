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
        var curRow = $(event.currentTarget.parentElement);
        curRow.removeClass('editing').html(jade.templates.metadatumView({
            key: this.key,
            value: this.value,
            accessLevel: this.accessLevel,
            girder: girder
        }));
    },

    save: function (event) {
        var curRow = $(event.currentTarget.parentElement),
            tempKey = curRow.find('.g-item-metadata-key-input').val(),
            tempValue = curRow.find('.g-item-metadata-value-input').val();

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
        }, this);

        if (this.new) {
            this.item.addMetadata(tempKey, tempValue, saveCallback);
        } else {
            this.item.editMetadata(tempKey, this.key, tempValue, saveCallback);
        }
    },

    initialize: function (settings) {
        this.item = settings.item;
        this.key = settings.key || '';
        this.value = settings.value || '';
        this.accessLevel = settings.accessLevel;
        this.new = settings.new;
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.metadatumEditWidget({
            item: this.item,
            key: this.key,
            value: this.value,
            accessLevel: this.accessLevel,
            girder: girder
        }));
        this.$el.find('.g-item-metadata-key-input').focus();

        return this;
    }

});
