var AssetstoreModel = require('girder/models/AssetstoreModel');
var Collection      = require('girder/collection');

var AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel
});

module.exports = AssetstoreCollection;
