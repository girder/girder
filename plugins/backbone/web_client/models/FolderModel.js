import $ from 'jquery';

import Model from './Model';
import CollectionModel from './CollectionModel';
import UserModel from './UserModel';

import FolderCollection from '../collections/FolderCollection';
import ItemCollection from '../collections/ItemCollection';

const FolderModel = Model.extend({
    resource: 'folder',
    parent() {
        const promise = $.Deferred();
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
        }
        if (parent) {
            promise.resolve(parent);
        } else {
            promise.reject('Unset or unknown parent type');
        }

        return promise.promise();
    },
    children() {
        return $.when(this.childFolders(), this.childItems())
            .then((folders, items) => [folders, items]);
    },

    childFolders() {
        return $.Deferred()
            .resolve(new FolderCollection([], {parent: this}))
            .promise();
    },

    childItems() {
        return $.Deferred()
            .resolve(new ItemCollection([], {parent: this}))
            .promise();
    }
});

export default FolderModel;
