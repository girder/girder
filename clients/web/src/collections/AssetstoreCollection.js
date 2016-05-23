import AssetstoreModel from 'girder/models/AssetstoreModel';
import Collection      from 'girder/collection';

export var AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel
});
