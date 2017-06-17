import Collection from './Collection';
import UserModel from '../models/UserModel';

const UserCollection = Collection.extend({
    resource: 'user',
    model: UserModel
});

export default UserCollection;
