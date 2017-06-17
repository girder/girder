import FolderCollection from '../collections/FolderCollection';
import Model from './Model';

const UserModel = Model.extend({
    resource: 'user',
    children() {
        return [new FolderCollection([], {parent: this})];
    }
});

export default UserModel;
