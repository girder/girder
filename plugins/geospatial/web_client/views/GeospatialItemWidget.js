import View from 'girder/views/View';

import GeospatialItemWidgetTemplate from '../templates/geospatialItemWidget.pug';
import '../stylesheets/geospatialItemWidget.styl';

var GeospatialItemWidget = View.extend({
    initialize: function (settings) {
        this.accessLevel = settings.accessLevel;
        this.item = settings.item;
        this.item.on('g:changed', function () {
            this.render();
        }, this);
        this.render();
    },
    render: function () {
        this.$el.html(GeospatialItemWidgetTemplate({
            item: this.item
        }));
        return this;
    }
});

export default GeospatialItemWidget;
