girder.collections.ItemCollection = girder.Collection.extend({
    resourceName: 'item',
    model: girder.models.ItemModel,

    pageLimit: 100
});
