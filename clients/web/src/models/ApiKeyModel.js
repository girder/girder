import _ from 'underscore';

import AccessControlledModel from 'girder/models/AccessControlledModel';
import { restRequest } from 'girder/rest';

var ApiKeyModel = AccessControlledModel.extend({
    resourceName: 'api_key',

    setActive: function (active) {
        return restRequest({
            path: 'api_key/' + this.id,
            method: 'PUT',
            data: {
                active: active
            }
        }).done(_.bind(function () {
            this.set({active: active});
            this.trigger('g:setActive');
        }, this));
    },

    save: function () {
        // Scope needs to be sent to the server as JSON
        var scope = this.get('scope');
        this.attributes.scope = JSON.stringify(scope);
        var promise = AccessControlledModel.prototype.save.call(this, arguments);
        // Restore scope to its original state
        this.attributes.scope = scope;
        return promise;
    }
});

export default ApiKeyModel;
