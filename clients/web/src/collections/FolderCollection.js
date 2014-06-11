girder.collections.FolderCollection = girder.Collection.extend({
    resourceName: 'folder',
    sortField: 'lowerName',
    model: girder.models.FolderModel,

    pageLimit: 100,

    comparator: null
});
