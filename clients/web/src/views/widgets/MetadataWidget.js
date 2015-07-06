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
