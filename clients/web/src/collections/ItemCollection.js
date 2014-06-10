girder.collections.ItemCollection = girder.Collection.extend({
    resourceName: 'item',
    sortField: 'lowerName',
    model: girder.models.ItemModel,

    pageLimit: 100,

    comparator: null
});
