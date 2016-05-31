import Collection from 'girder/collections/Collection';
import GroupModel from 'girder/models/GroupModel';

var GroupCollection = Collection.extend({
    resourceName: 'group',
    model: GroupModel
});

export default GroupCollection;
