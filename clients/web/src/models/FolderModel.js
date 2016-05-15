var _                     = require('underscore');
var AccessControlledModel = require('girder/model').AccessControlledModel;
var MetadataMixin         = require('girder/model').MetadataMixin;

var FolderModel = AccessControlledModel.extend({
    resourceName: 'folder'
});

_.extend(FolderModel.prototype, MetadataMixin);

module.exports = FolderModel;
