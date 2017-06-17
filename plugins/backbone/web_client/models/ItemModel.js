import FileCollection from '../collections/FileCollection';
import FolderModel from './FolderModel';
import Model from './Model';

const ItemModel = Model.extend({
    resource: 'item',
    children() {
        return $.Deferred()
            .resolve([new FileCollection([], {parent: this})])
            .promise();
    },
    parent() {
        return $.Deferred()
            .resolve(new FolderModel({_id: this.get('folderId')}))
            .promise();
    }
});

export default ItemModel;
