import Collection from 'girder/collection';
import FileModel from 'girder/models/FileModel';

var FileCollection = Collection.extend({
    resourceName: 'file',
    model: FileModel,

    pageLimit: 100
});

export default FileCollection;
