import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import Collection from '@girder/core/collections/Collection';

var AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel,
    pageLimit: 1000
});

export default AssetstoreCollection;
