/**
 * The Item Preview widget shows a preview of items under a given folder.
 * For now, the only supported item previews are image previews.
 */

girder.views.ItemPreviewWidget = girder.View.extend({

    _isSupportedItem: function (item) {
        return /(jpg|jpeg|png|gif)$/i.test(item.get('name'));
    },

    initialize: function (settings) {
        this.collection = new girder.collections.ItemCollection();

        this.collection.on('g:changed', function () {
            this.trigger('g:changed');
            this.render();
        }, this).fetch({
            folderId: settings.folderId
        });
    },

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

    render: function () {
        this.$el.html(girder.templates.itemPreviews({
            items: this.collection.filter(this._isSupportedItem),
            hasMore: this.collection.hasNextPage(),
            girder: girder,
        }));
        var view = this;
        return this;
    }

});

girder.wrap(girder.views.HierarchyWidget, 'render', function (render) {

    render.call(this);

    // Only on folder views:
    if (this.parentModel.resourceName === 'folder' && this._showItems) {

        // Add the item-previews-container.
        var element = $('<div class="g-item-previews-container">');
        this.$el.append(element);

        // Add the item preview widget into the container.
        this.itemPreviewView = new girder.views.ItemPreviewWidget({
            folderId: this.parentModel.get('_id'),
            parentView: this,
            el: element
        })
        .render();
    }

    return this;

});
