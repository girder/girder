import _ from 'underscore';

import Model from 'girder/models/Model';
import { restRequest } from 'girder/rest';

/**
 * Models corresponding to AccessControlledModels on the server should extend
 * from this object. It provides utilities for managing and storing the
 * access control list on
 */
var AccessControlledModel = Model.extend({
    /**
     * Saves the access control list on this model to the server. Saves the
     * state of whatever this model's "access" parameter is set to, which
     * should be an object of the form:
     *    {groups: [{id: <groupId>, level: <accessLevel>}, ...],
     *     users: [{id: <userId>, level: <accessLevel>}, ...]}
     * The "public" attribute of this model should also be set as a boolean.
     * When done, triggers the 'g:accessListSaved' event on the model.
     */
    updateAccess: function (params) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        return restRequest({
            path: (this.altUrl || this.resourceName) + '/' + this.get('_id') + '/access',
            type: 'PUT',
            data: _.extend({
                access: JSON.stringify(this.get('access')),
                public: this.get('public')
            }, params || {})
        }).done(_.bind(function () {
            this.trigger('g:accessListSaved');
        }, this)).error(_.bind(function (err) {
            this.trigger('g:error', err);
        }, this));
    },

    /**
     * Fetches the access control list from the server, and sets it as the
     * access property.
     * @param force By default, this only fetches access if it hasn't already
     *              been set on the model. If you want to force a refresh
     *              anyway, set this param to true.
     */
    fetchAccess: function (force) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        if (!this.get('access') || force) {
            return restRequest({
                path: (this.altUrl || this.resourceName) + '/' + this.get('_id') + '/access',
                type: 'GET'
            }).done(_.bind(function (resp) {
                if (resp.access) {
                    this.set(resp);
                } else {
                    this.set('access', resp);
                }
                this.trigger('g:accessFetched');
                return resp;
            }, this)).error(_.bind(function (err) {
                this.trigger('g:error', err);
            }, this));
        } else {
            this.trigger('g:accessFetched');
            return $.when(this.get('access'));
        }
    }
});

export default AccessControlledModel;
