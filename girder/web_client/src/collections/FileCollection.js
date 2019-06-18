import Collection from '@girder/core/collections/Collection';
import FileModel from '@girder/core/models/FileModel';

var FileCollection = Collection.extend({
    resourceName: 'file',
    model: FileModel,

    pageLimit: 100
});

export default FileCollection;
