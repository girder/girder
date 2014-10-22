girder.collections.FolderCollection = girder.Collection.extend({
    resourceName: 'folder',
    model: girder.models.FolderModel,

    pageLimit: 100
});
