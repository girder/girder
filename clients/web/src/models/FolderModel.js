import _ from 'underscore';

import AccessControlledModel from 'girder/models/AccessControlledModel';
import MetadataMixin from 'girder/models/MetadataMixin';
import { restRequest } from 'girder/rest';

var FolderModel = AccessControlledModel.extend({
    resourceName: 'folder',

    getRootPath: function () {
        return restRequest({
            url: `${this.resourceName}/${this.id}/rootpath`
        });
    }
});

_.extend(FolderModel.prototype, MetadataMixin);

export default FolderModel;
