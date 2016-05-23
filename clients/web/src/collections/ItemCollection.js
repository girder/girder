import Collection from 'girder/collection';
import ItemModel  from 'girder/models/ItemModel';

export var ItemCollection = Collection.extend({
    resourceName: 'item',
    model: ItemModel,

    pageLimit: 100
});
