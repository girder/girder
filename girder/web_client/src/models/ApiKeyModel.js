import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import { restRequest } from '@girder/core/rest';

var ApiKeyModel = AccessControlledModel.extend({
    resourceName: 'api_key',

    setActive: function (active) {
        return restRequest({
            url: `api_key/${this.id}`,
            method: 'PUT',
            data: {
                active: active
            }
        }).done(() => {
            this.set({active: active});
            this.trigger('g:setActive');
        });
    },

    save: function () {
        // Scope needs to be sent to the server as JSON
        var scope = this.get('scope');
        this.set('scope', JSON.stringify(scope), {silent: true}); // eslint-disable-line backbone/no-silent
        var promise = AccessControlledModel.prototype.save.call(this, arguments);
        // Restore scope to its original state
        this.set('scope', scope, {silent: true}); // eslint-disable-line backbone/no-silent
        return promise;
    }
});

export default ApiKeyModel;
