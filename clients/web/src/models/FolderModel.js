import _ from 'underscore';

import AccessControlledModel from 'girder/models/AccessControlledModel';
import MetadataMixin from 'girder/models/MetadataMixin';

var FolderModel = AccessControlledModel.extend({
    resourceName: 'folder'
});

_.extend(FolderModel.prototype, MetadataMixin);

export default FolderModel;
