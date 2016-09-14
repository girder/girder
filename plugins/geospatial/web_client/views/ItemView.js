import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import GeospatialItemWidget from './GeospatialItemWidget';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        var element = $('<div class="g-item-geospatial"/>');
        $('.g-item-metadata').after(element);
        this.geospatialItemWidget = new GeospatialItemWidget({
            accessLevel: this.accessLevel,
            el: element,
            item: this.model,
            parentView: this
        });
    }, this);

    return render.call(this);
});
