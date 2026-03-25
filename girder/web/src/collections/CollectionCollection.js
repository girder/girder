import Collection from '@girder/core/collections/Collection';
import CollectionModel from '@girder/core/models/CollectionModel';

var CollectionCollection = Collection.extend({
    resourceName: 'collection',
    model: CollectionModel
});

export default CollectionCollection;
