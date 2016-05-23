import Collection from 'girder/collection';
import FileModel  from 'girder/models/FileModel';

export var FileCollection = Collection.extend({
    resourceName: 'file',
    model: FileModel,

    pageLimit: 100
});
