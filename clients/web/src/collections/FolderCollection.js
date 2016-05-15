var Collection  = require('girder/collection');
var FolderModel = require('girder/models/FolderModel');

var FolderCollection = Collection.extend({
    resourceName: 'folder',
    model: FolderModel,

    pageLimit: 100
});

module.exports = FolderCollection;
