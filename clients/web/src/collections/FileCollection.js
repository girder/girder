var Collection = require('girder/collection');
var FileModel  = require('girder/models/FileModel');

var FileCollection = Collection.extend({
    resourceName: 'file',
    model: FileModel,

    pageLimit: 100
});

module.exports = FileCollection;
