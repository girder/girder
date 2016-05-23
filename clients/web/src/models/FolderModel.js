import _ from 'underscore';

import { MetadataMixin, AccessControlledModel } from 'girder/model';

export var FolderModel = AccessControlledModel.extend({
    resourceName: 'folder'
});

_.extend(FolderModel.prototype, MetadataMixin);
