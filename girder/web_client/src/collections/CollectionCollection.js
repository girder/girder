import Collection from 'girder/collections/Collection';
import CollectionModel from 'girder/models/CollectionModel';

var CollectionCollection = Collection.extend({
    resourceName: 'collection',
    model: CollectionModel
});

export default CollectionCollection;
