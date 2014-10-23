girder.models.FolderModel = girder.AccessControlledModel.extend({
    resourceName: 'folder'
});

_.extend(girder.models.FolderModel.prototype, girder.models.MetadataMixin);
