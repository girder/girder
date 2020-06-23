import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import Collection from '@girder/core/collections/Collection';

const AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel
});

export default AssetstoreCollection;
