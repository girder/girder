var Collection      = require('girder/collection');
var CollectionModel = require('girder/models/CollectionModel');

var CollectionCollection = Collection.extend({
    resourceName: 'collection',
    model: CollectionModel
});

module.exports = CollectionCollection;
