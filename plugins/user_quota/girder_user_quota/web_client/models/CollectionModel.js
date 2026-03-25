import extendModel from './extendModel';

const CollectionModel = girder.models.CollectionModel;

extendModel(CollectionModel, 'collection');
