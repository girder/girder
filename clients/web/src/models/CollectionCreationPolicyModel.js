import _ from 'underscore';
import AccessControlledModel from 'girder/models/AccessControlledModel';
import { restRequest } from 'girder/rest';

var CollectionCreationPolicyModel = AccessControlledModel.extend({
    resourceName: 'system/setting/collection_creation_policy',
    fetchAccess: function () {
        return restRequest({
            path: this.resourceName + '/access',
            type: 'GET'
        }).done(_.bind(function (resp) {
            this.set('access', resp);
            this.trigger('g:accessFetched');
            return resp;
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    }
});

export default CollectionCreationPolicyModel;
