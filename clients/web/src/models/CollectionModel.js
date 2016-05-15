var AccessControlledModel = require('girder/model').AccessControlledModel;

var CollectionModel = AccessControlledModel.extend({
    resourceName: 'collection'
});

module.exports = CollectionModel;
