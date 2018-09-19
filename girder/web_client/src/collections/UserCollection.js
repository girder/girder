import Collection from 'girder/collections/Collection';
import UserModel from 'girder/models/UserModel';
import { restRequest } from 'girder/rest';

var UserCollection = Collection.extend({
    resourceName: 'user',
    model: UserModel,

    // Override default sort field
    sortField: 'lastName',
    secondarySortField: 'firstName'
}, {
    getTotalCount: function () {
        return restRequest({
            url: 'user/details',
            method: 'GET'
        })
            .then((resp) => {
                return resp['nUsers'];
            });
    }
});

export default UserCollection;
