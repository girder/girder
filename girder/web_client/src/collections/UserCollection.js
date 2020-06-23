import Collection from '@girder/core/collections/Collection';
import UserModel from '@girder/core/models/UserModel';
import { restRequest } from '@girder/core/rest';

const UserCollection = Collection.extend({
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
                return resp.nUsers;
            });
    }
});

export default UserCollection;
