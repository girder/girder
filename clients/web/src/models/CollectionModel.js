import AccessControlledModel from 'girder/models/AccessControlledModel';

var CollectionModel = AccessControlledModel.extend({
    resourceName: 'collection'
});

export default CollectionModel;
