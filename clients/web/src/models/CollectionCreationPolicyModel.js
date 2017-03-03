import AccessControlledModel from 'girder/models/AccessControlledModel';
import { restRequest } from 'girder/rest';

var CollectionCreationPolicyModel = AccessControlledModel.extend({
    resourceName: 'system/setting/collection_creation_policy',
    fetchAccess: function () {
        return restRequest({
            path: this.resourceName + '/access',
            type: 'GET'
        }).done(resp => {
            this.set('access', resp);
            this.trigger('g:accessFetched');
            return resp;
        }).error(err => {
            this.trigger('g:error', err);
        });
    }
});

export default CollectionCreationPolicyModel;
