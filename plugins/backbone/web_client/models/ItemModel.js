import FileCollection from '../collections/FileCollection';
import FolderModel from './FolderModel';
import Model from './Model';

const ItemModel = Model.extend({
    resource: 'item',
    children() {
        return [new FileCollection([], {parent: this})];
    },
    parent() {
        return new FolderModel({_id: this.get('folderId')});
    }
});

export default ItemModel;
