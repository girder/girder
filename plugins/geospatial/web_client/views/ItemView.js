import _ from 'underscore';

import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import GeospatialItemWidget from './GeospatialItemWidget';

wrap(ItemView, 'render', function (render) {
    this.model.getAccessLevel(_.bind(function (accessLevel) {
        render.call(this);
        var element = $('<div class="g-item-geospatial"/>');
        $('.g-item-metadata').after(element);
        this.geospatialItemWidget = new GeospatialItemWidget({
            accessLevel: accessLevel,
            el: element,
            item: this.model,
            parentView: this
        });
    }, this));

    return this;
});
