import Collection from 'girder/collection';
import GroupModel from 'girder/models/GroupModel';

export var GroupCollection = Collection.extend({
    resourceName: 'group',
    model: GroupModel
});
