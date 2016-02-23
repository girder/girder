/**
 * This widget shows a list of items under a given folder.
 */
girder.views.ItemPreviewWidget = girder.View.extend({
    events: {
        'click a.g-item-preview-link': function (event) {
            // TODO: trigger a 'g:itemClicked' based on cid 
            // or other method rather than this lazy link proxy:
            var name = $(event.currentTarget).attr('g-item-name');
            $('.g-item-list a').filter(function(i, d) {
                return (name === $(d).text())
            }).click();
        },
    },

    initialize: function (settings) {

        new girder.views.LoadingAnimation({
            el: this.$el,
            parentView: this
        }).render();

        this.collection = new girder.collections.ItemCollection();
        this.collection.append = true; // Append, don't replace pages
        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.render();
        }, this).fetch({
            folderId: settings.folderId
        });
    },

    render: function () {
        this.$el.html(girder.templates.itemPreview({
            items: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            girder: girder,
        }));

        var view = this;
        return this;
    },

});
