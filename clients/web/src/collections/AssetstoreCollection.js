import AssetstoreModel from 'girder/models/AssetstoreModel';
import Collection from 'girder/collections/Collection';

var AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel
});

export default AssetstoreCollection;
