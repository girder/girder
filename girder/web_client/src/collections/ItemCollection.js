import Collection from '@girder/core/collections/Collection';
import ItemModel from '@girder/core/models/ItemModel';

const ItemCollection = Collection.extend({
    resourceName: 'item',
    model: ItemModel,

    pageLimit: 100
});

export default ItemCollection;
