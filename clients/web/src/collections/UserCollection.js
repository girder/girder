girder.collections.UserCollection = girder.Collection.extend({
    resourceName: 'user',
    model: girder.models.UserModel,

    // Override default sort field
    sortField: 'lastName',
    secondarySortField: 'firstName'
});
