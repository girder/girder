import ItemModel from './ItemModel';
import Model from './Model';

const FileModel = Model.extend({
    resource: 'file',
    parent() {
        return new ItemModel({_id: this.get('itemId')});
    }
});

export default FileModel;
