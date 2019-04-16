import Collection from '@girder/core/collections/Collection';
import GroupModel from '@girder/core/models/GroupModel';

var GroupCollection = Collection.extend({
    resourceName: 'group',
    model: GroupModel
});

export default GroupCollection;
