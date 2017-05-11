import ItemCollection from 'girder/collections/ItemCollection';

var ItemTaskCollection = ItemCollection.extend({
    pageLimit: 20,
    altUrl: 'item_task'
});

export default ItemTaskCollection;
