import AssetstoreModel from 'girder/models/AssetstoreModel';
import Collection from 'girder/collection';

var AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel
});

export default AssetstoreCollection;
