import Collection from './Collection';
import CollectionModel from '../models/CollectionModel';

const CollectionCollection = Collection.extend({
    resource: 'collection',
    model: CollectionModel
});

export default CollectionCollection;
