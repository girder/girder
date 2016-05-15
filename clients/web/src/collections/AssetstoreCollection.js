var Collection      = require('girder/collection');
var AssetstoreModel = require('girder/models/AssetstoreModel');

var AssetstoreCollection = Collection.extend({
    resourceName: 'assetstore',
    model: AssetstoreModel
});

module.exports = AssetstoreCollection;
