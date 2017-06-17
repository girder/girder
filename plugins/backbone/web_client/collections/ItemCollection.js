import _ from 'underscore';

import Collection from './Collection';
import ItemModel from '../models/ItemModel';

const ItemCollection = Collection.extend({
    resource: 'item',
    model: ItemModel
});

ItemCollection.prototype.queryParams = _.extend({
    folderId() {
        return this.parent.id;
    }
}, ItemCollection.prototype.queryParams);
export default ItemCollection;
