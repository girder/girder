import ItemModel from './ItemModel';
import Model from './Model';

const FileModel = Model.extend({
    resource: 'file',
    parent() {
        return $.Deferred()
            .resolve(new ItemModel({_id: this.get('itemId')}))
            .promise();
    }
});

export default FileModel;
