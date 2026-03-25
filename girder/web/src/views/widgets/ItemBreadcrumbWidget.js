import $ from 'jquery';

import router from '@girder/core/router';
import View from '@girder/core/views/View';

import ItemBreadcrumbTemplate from '@girder/core/templates/widgets/itemBreadcrumb.pug';

/**
 * Renders the a breadcrumb for the item page
 */
var ItemBreadcrumbWidget = View.extend({
    events: {
        'click a.g-item-breadcrumb-link': function (event) {
            var link = $(event.currentTarget);
            router.navigate(link.data('type') + '/' + link.data('id'),
                { trigger: true });
        },
        'click a.g-hierarchy-level-up': function () {
            var folder = this.parentChain.pop().object;
            router.navigate('folder/' + folder._id, { trigger: true });
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
