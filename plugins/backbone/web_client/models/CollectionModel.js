import Model from './Model';
import FolderCollection from '../collections/FolderCollection';

const CollectionModel = Model.extend({
    resource: 'collection',
    children() {
        return [new FolderCollection([], {parent: this})];
    }
});

export default CollectionModel;
