import $ from 'jquery';
import _ from 'underscore';

import Model from '@girder/core/models/Model';
import { restRequest } from '@girder/core/rest';

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
            throw new Error('An altUrl or resourceName must be set on the Model.');
        }

        return restRequest({
            url: `${this.altUrl || this.resourceName}/${this.id}/access`,
            method: 'PUT',
            data: _.extend({
                access: JSON.stringify(this.get('access')),
                public: this.get('public'),
                publicFlags: JSON.stringify(this.get('publicFlags') || [])
            }, params || {})
        }).done(() => {
            this.trigger('g:accessListSaved');
        }).fail((err) => {
            this.trigger('g:error', err);
        });
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
            throw new Error('An altUrl or resourceName must be set on the Model.');
        }

        if (!this.get('access') || force) {
            return restRequest({
                url: `${this.altUrl || this.resourceName}/${this.id}/access`,
                method: 'GET'
            }).done((resp) => {
                if (resp.access) {
                    this.set(resp);
                } else {
                    this.set('access', resp);
                }
                this.trigger('g:accessFetched');
                return resp;
            }).fail((err) => {
                this.trigger('g:error', err);
            });
        } else {
            this.trigger('g:accessFetched');
            return $.Deferred().resolve(this.get('access')).promise();
        }
    }
});

export default AccessControlledModel;
