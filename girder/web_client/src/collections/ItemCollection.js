import Collection from '@girder/core/collections/Collection';
import ItemModel from '@girder/core/models/ItemModel';

var ItemCollection = Collection.extend({
    resourceName: 'item',
    model: ItemModel,

    pageLimit: 100
});

export default ItemCollection;
