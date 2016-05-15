var Collection = require('girder/collection');
var ItemModel  = require('girder/models/ItemModel');

var ItemCollection = Collection.extend({
    resourceName: 'item',
    model: ItemModel,

    pageLimit: 100
});

module.exports = ItemCollection;
