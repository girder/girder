import AccessControlledModel from 'girder/models/AccessControlledModel';
import { restRequest } from 'girder/rest';

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
