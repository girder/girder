import AccessControlledModel from '@girder/core/models/AccessControlledModel';

var CollectionModel = AccessControlledModel.extend({
    resourceName: 'collection'
});

export default CollectionModel;
