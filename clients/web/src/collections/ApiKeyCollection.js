import ApiKeyModel from 'girder/models/ApiKeyModel';
import Collection from 'girder/collections/Collection';

var ApiKeyCollection = Collection.extend({
    resourceName: 'api_key',
    model: ApiKeyModel
});

export default ApiKeyCollection;
