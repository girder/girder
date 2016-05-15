var Collection = require('girder/collection');
var GroupModel = require('girder/models/GroupModel');

var GroupCollection = Collection.extend({
    resourceName: 'group',
    model: GroupModel
});

module.exports = GroupCollection;
