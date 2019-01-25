import AssetstoreCollection from '@girder/core/collections/AssetstoreCollection';
import { getCurrentUser } from '@girder/core/auth';
import { restRequest } from '@girder/core/rest';

function extendModel(Model, modelType) {
    /* Saves the quota policy on this model to the server.  Saves the
     * state of whatever this model's "quotaPolicy" parameter is set
     * to.  When done, triggers the 'g:quotaPolicySaved' event on the
     * model.
     */
    Model.prototype.updateQuotaPolicy = function () {
        restRequest({
            url: `${this.resourceName}/${this.id}/quota`,
            method: 'PUT',
            error: null,
            data: {
                policy: JSON.stringify(this.get('quotaPolicy'))
            }
        }).done(() => {
            this.trigger('g:quotaPolicySaved');
        }).fail((err) => {
            this.trigger('g:error', err);
        });

        return this;
    };

    /* Fetches the quota policy from the server, and sets it as the
     * quotaPolicy property.
     * @param force: By default, this only fetches quotaPolicy if it
     *               hasn't already been set on the model.  If you want
     *               to force a refresh anyway, set this param to true.
     */
    Model.prototype.fetchQuotaPolicy = function (force) {
        this.off('g:fetched').on('g:fetched', function () {
            this.fetchAssetstores(force);
        });
        if (!this.get('quotaPolicy') || force) {
            restRequest({
                url: `${this.resourceName}/${this.id}/quota`,
                method: 'GET'
            }).done((resp) => {
                this.set('quotaPolicy', resp.quota);
                this.fetch();
            }).fail((err) => {
                this.trigger('g:error', err);
            });
        } else {
            this.fetch();
        }
        return this;
    };

    /* Fetches the list of assetstores from the server, and sets it as
     * the assetstoreList property.  This is the second part of
     * fetching quota policy, as we need to know the assetstores for
     * the user interface.
     * @param force: By default, this only fetches assetstoreList if it
     *               hasn't already been set on the model.  If you want
     *               to force a refresh anyway, set this param to true.
     */
    Model.prototype.fetchAssetstores = function (force) {
        if (getCurrentUser().get('admin') &&
                (!this.get('assetstoreList') || force)) {
            this.set('assetstoreList',
                new AssetstoreCollection());
            this.get('assetstoreList').on('g:changed', function () {
                this.fetchDefaultQuota(force);
            }, this).fetch();
        } else {
            this.fetchDefaultQuota(force);
        }
        return this;
    };

    /* Fetches the global default setting for quota for this resource.
     * @param force: By default, this only fetches the default quota if
     *               it hasn't already been set on the model.  If you
     *               want to force a refresh anyway, set this param to
     *               true.
     */
    Model.prototype.fetchDefaultQuota = function (force) {
        if (getCurrentUser().get('admin') &&
                (!this.get('defaultQuota') || force)) {
            restRequest({
                url: 'system/setting',
                method: 'GET',
                data: {
                    key: 'user_quota.default_' + modelType + '_quota'
                }
            }).done((resp) => {
                this.set('defaultQuota', resp);
                this.trigger('g:quotaPolicyFetched');
            });
        } else {
            this.trigger('g:quotaPolicyFetched');
        }
        return this;
    };
}

export default extendModel;
