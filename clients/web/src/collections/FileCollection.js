import Collection from 'girder/collections/Collection';
import FileModel from 'girder/models/FileModel';

var FileCollection = Collection.extend({
    resourceName: 'file',
    model: FileModel,

    pageLimit: 100
});

export default FileCollection;
