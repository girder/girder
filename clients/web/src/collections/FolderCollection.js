import Collection  from 'girder/collection';
import FolderModel from 'girder/models/FolderModel';

export var FolderCollection = Collection.extend({
    resourceName: 'folder',
    model: FolderModel,

    pageLimit: 100
});
