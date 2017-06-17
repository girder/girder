import Model from './Model';
import CollectionModel from './CollectionModel';
import UserModel from './UserModel';

import FolderCollection from '../collections/FolderCollection';
import ItemCollection from '../collections/ItemCollection';

const FolderModel = Model.extend({
    resource: 'folder',
    parent() {
        let parent;
        switch (this.get('parentType')) {
            case 'folder':
                parent = new FolderModel({_id: this.get('parentId')});
                break;
            case 'collection':
                parent = new CollectionModel({_id: this.get('parentId')});
                break;
            case 'user':
                parent = new UserModel({_id: this.get('parentId')});
                break;
            default:
                throw new Error('Unknown parent type');
        }
        return parent;
    },
    children() {
        return [this.items(), this.folders()];
    },

    folders() {
        return new FolderCollection([], {parent: this});
    },

    items() {
        return new ItemCollection([], {parent: this});
    }
});

export default FolderModel;
