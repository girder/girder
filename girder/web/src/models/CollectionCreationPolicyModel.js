import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import { restRequest } from '@girder/core/rest';

var CollectionCreationPolicyModel = AccessControlledModel.extend({
    resourceName: 'system/setting/collection_creation_policy',
    fetchAccess: function () {
        return restRequest({
            url: `${this.resourceName}/access`,
            method: 'GET'
        }).done((resp) => {
            this.set('access', resp);
            this.trigger('g:accessFetched');
            return resp;
        }).fail((err) => {
            this.trigger('g:error', err);
        });
    }
});

export default CollectionCreationPolicyModel;
