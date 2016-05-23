import Collection from 'girder/collection';
import UserModel  from 'girder/models/UserModel';

export var UserCollection = Collection.extend({
    resourceName: 'user',
    model: UserModel,

    // Override default sort field
    sortField: 'lastName',
    secondarySortField: 'firstName'
});
