/**
 * All models should descend from this base model, which provides a number
 * of utilities for synchronization.
 */
girder.Model = Backbone.Model.extend({
    resourceName: null,

    /**
     * Get the name for this resource. By default, just the name attribute.
     */
    name: function () {
        return this.get('name');
    },

    /**
     * Save this model to the server. If this is a new model, meaning it has no
     * _id attribute, this will create it. If the _id is set, we update the
     * existing model. Triggers g:saved on success, and g:error on error.
     */
    save: function () {
        if (this.resourceName === null) {
            alert('Error: You must set a resourceName on your model.');
            return;
        }

        var path, type;
        if (this.has('_id')) {
            path = this.resourceName + '/' + this.get('_id');
            type = 'PUT';
        }
        else {
            path = this.resourceName;
            type = 'POST';
        }

        girder.restRequest({
            path: path,
            type: type,
            data: this.attributes,
            error: null // don't do default error behavior (validation may fail)
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:saved');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Fetch a single resource from the server. Triggers g:fetched on success,
     * or g:error on error.
     */
    fetch: function () {
        if (this.resourceName === null) {
            alert('Error: You must set a resourceName on your model.');
            return;
        }

        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id'),
            error: null
        }).done(_.bind(function (resp) {
            this.set(resp);
            this.trigger('g:fetched');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Delete the model on the server.
     * @param throwError Whether to throw an error (bool, default=true)
     */
    destroy: function (throwError) {
        if (this.resourceName === null) {
            alert('Error: You must set a resourceName on your model.');
            return;
        }

        var params = {
            path: this.resourceName + '/' + this.get('_id'),
            type: 'DELETE'
        };

        if (throwError !== false) {
            params.error = null;
        }

        girder.restRequest(params).done(_.bind(function () {
            if (this.collection) {
                this.collection.remove(this);
            }
            this.trigger('g:deleted');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Return the access level with respect to the current user
     */
    getAccessLevel: function () {
        return this.get('_accessLevel');
    }

});

/**
 * Models corresponding to AccessControlledModels on the server should extend
 * from this object. It provides utilities for managing and storing the
 * access control list on
 */
girder.AccessControlledModel = girder.Model.extend({
    /**
     * Saves the access control list on this model to the server. Saves the
     * state of whatever this model's "access" parameter is set to, which
     * should be an object of the form:
     *    {groups: [{id: <groupId>, level: <accessLevel>}, ...],
     *     users: [{id: <userId>, level: <accessLevel>}, ...]}
     * The "public" attribute of this model should also be set as a boolean.
     * When done, triggers the 'g:accessListSaved' event on the model.
     */
    updateAccess: function () {
        if (this.resourceName === null) {
            alert('Error: You must set a resourceName on your model.');
            return;
        }

        girder.restRequest({
            path: this.resourceName + '/' + this.get('_id') + '/access',
            type: 'PUT',
            data: {
                'access': JSON.stringify(this.get('access')),
                'public': this.get('public')
            }
        }).done(_.bind(function () {
            this.trigger('g:accessListSaved');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));

        return this;
    },

    /**
     * Fetches the access control list from the server, and sets it as the
     * access property.
     * @param force By default, this only fetches access if it hasn't already
     *              been set on the model. If you want to force a refresh
     *              anyway, set this param to true.
     */
    fetchAccess: function (force) {
        if (this.resourceName === null) {
            alert('Error: You must set a resourceName on your model.');
            return;
        }

        if (!this.get('access') || force) {
            girder.restRequest({
                path: this.resourceName + '/' + this.get('_id') + '/access',
                type: 'GET'
            }).done(_.bind(function (resp) {
                if (resp.access) {
                    this.set(resp);
                }
                else {
                    this.set('access', resp);
                }
                this.trigger('g:accessFetched');
            }, this)).error(_.bind(function (err) {
                this.trigger('g:error', err);
            }, this));
        }
        else {
            this.trigger('g:accessFetched');
        }

        return this;
    }
});
