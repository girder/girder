import _ from 'underscore';

import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import MetadataMixin from '@girder/core/models/MetadataMixin';
import { restRequest } from '@girder/core/rest';

var FolderModel = AccessControlledModel.extend({
    resourceName: 'folder',

    getRootPath: function () {
        return restRequest({
            url: `${this.resourceName}/${this.id}/rootpath`
        });
    },

    /**
     * Remove the contents of the folder.
     */
    removeContents: function () {
        return restRequest({
            url: `${this.resourceName}/${this.id}/contents`,
            method: 'DELETE'
        }).done((resp) => {
            this.trigger('g:success');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    }
});

_.extend(FolderModel.prototype, MetadataMixin);

export default FolderModel;
