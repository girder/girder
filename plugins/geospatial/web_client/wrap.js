import _ from 'underscore';

import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

import ItemModel from 'girder/models/ItemModel';
wrap(ItemModel, 'fetch', function (fetch) {
    fetch.call(this);
    restRequest({
        path: this.resourceName + '/' + this.get('_id') + '/geospatial',
        error: null
    }).done(_.bind(function (resp) {
        this.set(resp);
    }, this)).error(_.bind(function (err) {
        this.trigger('g:error', err);
    }, this));
    return this;
});

import ItemView from 'girder/views/body/ItemView';
import ItemWidget from './views/ItemWidget';
wrap(ItemView, 'render', function (render) {
    this.model.getAccessLevel(_.bind(function (accessLevel) {
        render.call(this);
        var element = $('<div class="g-item-geospatial"/>');
        $('.g-item-metadata').after(element);
        this.geospatialItemWidget = new ItemWidget({
            accessLevel: accessLevel,
            el: element,
            item: this.model,
            parentView: this
        });
    }, this));

    return this;
});
