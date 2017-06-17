import _ from 'underscore';

import Collection from './Collection';
import FolderModel from '../models/FolderModel';

const FolderCollection = Collection.extend({
    resource: 'folder',
    model: FolderModel
});

FolderCollection.prototype.queryParams = _.extend({
    parentId() {
        return this.parent.id;
    },
    parentType() {
        return this.parent.resource;
    }
}, FolderCollection.prototype.queryParams);

export default FolderCollection;
