/**
 * This widget shows a list of metadata in a given item.
 */
girder.views.MetadataWidget = girder.View.extend({
    events: {
        'click .g-widget-metadata-add-button': 'addMetadata',
        'click .g-widget-metadata-edit-button': 'editMetadata'
    },

    addMetadata: function () {
        var newRow = $('<div>').attr({
            class: 'g-widget-metadata-row editing'
        }).appendTo(this.$el.find('.g-widget-metadata-container'));
        this.metadatumEditWidget = new girder.views.MetadatumEditWidget({
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
        this.metadatumEditWidget = new girder.views.MetadatumEditWidget({
            el: row,
            item: this.item,
            key: row.attr('g-key'),
            value: row.attr('g-value'),
            accessLevel: this.accessLevel,
            newDatum: false,
            parentView: this
        });
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
            if (typeof value === 'object') {
                value = JSON.stringify(value);
            }
            metaList.push({key: metaKeys[i], value: value});
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
    }

});
