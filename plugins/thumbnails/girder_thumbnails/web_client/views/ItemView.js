import ItemViewTemplate from '../templates/itemView.pug';

import FlowView from './FlowView';

const _ = girder._;
const ItemView = girder.views.body.ItemView;
const { wrap } = girder.utilities.PluginUtils;
const FileCollection = girder.collections.FileCollection;

// Show thumbnails on the item page
wrap(ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        const thumbnails = new FileCollection(
            _.map(this.model.get('_thumbnails'), (id) => ({ _id: id }))
        );

        if (thumbnails && thumbnails.length) {
            this.$('.g-item-info').before(ItemViewTemplate());

            new FlowView({
                className: 'g-thumbnails-flow-view-container',
                parentView: this,
                thumbnails: thumbnails,
                accessLevel: this.model.getAccessLevel()
            })
                .render()
                .$el.insertBefore(this.$('.g-item-info'));
        }
    }, this);

    render.call(this);
});
