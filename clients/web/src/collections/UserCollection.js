var Collection = require('girder/collection');
var UserModel  = require('girder/models/UserModel');

var UserCollection = Collection.extend({
    resourceName: 'user',
    model: UserModel,

    // Override default sort field
    sortField: 'lastName',
    secondarySortField: 'firstName'
});

module.exports = UserCollection;
