import Model from './Model';
import FolderCollection from '../collections/FolderCollection';

const CollectionModel = Model.extend({
    resource: 'collection',
    children() {
        return $.Deferred()
            .resolve([new FolderCollection([], {parent: this})])
            .promise();
    }
});

export default CollectionModel;
