import FolderCollection from '../collections/FolderCollection';
import Model from './Model';

const UserModel = Model.extend({
    resource: 'user',
    children() {
        return $.Deferred()
            .resolve([new FolderCollection([], {parent: this})])
            .promise();
    }
});

export default UserModel;
