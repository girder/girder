import $ from 'jquery';

import router from 'girder/router';
import View from 'girder/views/View';

import ItemBreadcrumbTemplate from 'girder/templates/widgets/itemBreadcrumb.pug';

/**
 * Renders the a breadcrumb for the item page.
 * This widget is the only entry point to the 'folderView', and this brings inconstancy on the way to access
 * the same resource, in fact there are two different routes :
 * - '#collection/{collection_id}/folder/{folder_id}'
 * - '#folder/{folder_id}'
 * The first one inherits from the collection view
 * The second one from the folder view
 *
 * So it become possible to be on the 'folderView' to access to a collection.
 * TODO: Remove or make some limitation to avoid this kind of confusion
 */
var ItemBreadcrumbWidget = View.extend({
    events: {
        'click a.g-item-breadcrumb-link': function (event) {
            var link = $(event.currentTarget);
            router.navigate(link.data('type') + '/' + link.data('id'),
                {trigger: true});
        },
        'click a.g-hierarchy-level-up': function () {
            var folder = this.parentChain.pop().object;
            router.navigate('folder/' + folder._id, {trigger: true});
        }
    },

    initialize: function (settings) {
        this.parentChain = settings.parentChain;
        this.render();
    },

    render: function () {
        this.$el.html(ItemBreadcrumbTemplate({
            parentChain: this.parentChain
        }));

        return this;
    }
});

export default ItemBreadcrumbWidget;
