import _ from 'underscore';

import ItemModel from 'girder/models/ItemModel';
import { restRequest } from 'girder/rest';
import { wrap } from 'girder/utilities/PluginUtils';

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
