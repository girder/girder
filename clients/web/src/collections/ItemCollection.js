import Collection from 'girder/collection';
import ItemModel  from 'girder/models/ItemModel';

var ItemCollection = Collection.extend({
    resourceName: 'item',
    model: ItemModel,

    pageLimit: 100
});

export default ItemCollection;
