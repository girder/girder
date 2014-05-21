/**
 * This widget shows a list of files in a given item.
 */
girder.views.MetadataWidget = girder.View.extend({
    events: {},

    initialize: function (settings) {
        this.item = settings.item;
        this.item.on('g:changed', function () {
            this.render();
        }, this);
        this.render();
    },

    render: function () {
        this.$el.html(jade.templates.metadataWidget({
            item: this.item,
            girder: girder
        }));

        return this;
    }

});
