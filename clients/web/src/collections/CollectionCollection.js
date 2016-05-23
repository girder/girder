import Collection      from 'girder/collection';
import CollectionModel from 'girder/models/CollectionModel';

export var CollectionCollection = Collection.extend({
    resourceName: 'collection',
    model: CollectionModel
});
