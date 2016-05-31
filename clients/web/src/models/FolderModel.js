import _ from 'underscore';

import { MetadataMixin, AccessControlledModel } from 'girder/models/Model';

var FolderModel = AccessControlledModel.extend({
    resourceName: 'folder'
});

_.extend(FolderModel.prototype, MetadataMixin);

export default FolderModel;
