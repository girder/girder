import View from 'girder/views/View';

import ItemTemplate from '../templates/item.jade';
import '../stylesheets/item.styl';

var ItemWidget = View.extend({
    initialize: function (settings) {
        this.accessLevel = settings.accessLevel;
        this.item = settings.item;
        this.item.on('g:changed', function () {
            this.render();
        }, this);
        this.render();
    },
    render: function () {
        this.$el.html(ItemTemplate({
            item: this.item
        }));
        return this;
    }
});

export default ItemWidget;
