import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import GeospatialItemWidget from './GeospatialItemWidget';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        this.geospatialItemWidget = new GeospatialItemWidget({
            className: 'g-item-geospatial',
            accessLevel: this.accessLevel,
            item: this.model,
            parentView: this
        });
        this.geospatialItemWidget.$el.insertAfter(this.$('.g-item-metadata'));
    }, this);

    return render.call(this);
});
