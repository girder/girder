girder.collections.FileCollection = girder.Collection.extend({
    resourceName: 'file',

    model: girder.models.FileModel,

    pageLimit: 100
});
