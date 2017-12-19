import $ from 'jquery';

import router from 'girder/router';
import View from 'girder/views/View';

import IteamBreadcrumbTemplate from 'girder/templates/widgets/itemBreadcrumb.pug';

/**
 * Renders the a breadcrumb for the item page
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
        this.$el.html(IteamBreadcrumbTemplate({
            parentChain: this.parentChain
        }));

        return this;
    }
});

export default ItemBreadcrumbWidget;
