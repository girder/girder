girder.models.ApiKeyModel = girder.AccessControlledModel.extend({
    resourceName: 'api_key',

    setActive: function (active) {
        girder.restRequest({
            path: 'api_key/' + this.id,
            method: 'PUT',
            data: {
                active: active
            }
        }).done(_.bind(function () {
            this.set({active: active});
            this.trigger('g:setActive');
        }, this));

        return this;
    },

    save: function () {
        // Scope needs to be sent to the server as JSON
        var scope = this.get('scope');
        this.attributes.scope = JSON.stringify(scope);
        girder.AccessControlledModel.prototype.save.call(this, arguments);
        // Restore scope to its original state
        this.attributes.scope = scope;
    }
});
