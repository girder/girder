import ApiKeyModel from '@girder/core/models/ApiKeyModel';
import Collection from '@girder/core/collections/Collection';

var ApiKeyCollection = Collection.extend({
    resourceName: 'api_key',
    model: ApiKeyModel
});

export default ApiKeyCollection;
