import Collection from 'girder/collection';
import GroupModel from 'girder/models/GroupModel';

var GroupCollection = Collection.extend({
    resourceName: 'group',
    model: GroupModel
});

export default GroupCollection;
