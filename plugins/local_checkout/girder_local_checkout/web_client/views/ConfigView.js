import $ from 'jquery';

import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import { formatDate, formatSize, DATE_MINUTE } from '@girder/core/misc';
import { AssetstoreType } from '@girder/core/constants';

import template from '../templates/config.pug';

const SETTING_KEYS = [
    'local_checkout.assetstore_id',
    'local_checkout.max_days',
    'local_checkout.admin_only'
];

const ConfigView = View.extend({
    events: {
        'submit #g-local-checkout-config-form': function (event) {
            event.preventDefault();
            this.$('#g-local-checkout-error-message').empty();

            this._saveSettings([{
                key: 'local_checkout.assetstore_id',
                value: this.$('#g-local-checkout-assetstore').val()
            }, {
                key: 'local_checkout.max_days',
                value: parseInt(this.$('#g-local-checkout-max-days').val(), 10)
            }, {
                key: 'local_checkout.admin_only',
                value: this.$('#g-local-checkout-admin-only').is(':checked')
            }]);
        }
    },

    initialize: function () {
        this.breadcrumb = new PluginConfigBreadcrumbWidget({
            pluginName: 'Local Checkout',
            parentView: this
        });

        $.when(
            restRequest({
                url: 'system/setting',
                method: 'GET',
                data: { list: JSON.stringify(SETTING_KEYS) }
            }),
            restRequest({ url: 'assetstore', method: 'GET', data: { limit: 0 } }),
            restRequest({ url: 'local_checkout', method: 'GET', data: { limit: 0 } })
        ).done((settings, assetstores, checkouts) => {
            this.settings = settings[0];
            this.assetstores = assetstores[0].filter(
                (assetstore) => assetstore.type === AssetstoreType.FILESYSTEM);
            this.checkouts = checkouts[0];
            this.render();
        });
    },

    render: function () {
        this.$el.html(template({
            settings: this.settings,
            assetstores: this.assetstores,
            checkouts: this.checkouts,
            formatDate,
            formatSize,
            DATE_MINUTE
        }));
        this.breadcrumb.setElement(this.$('.g-config-breadcrumb-container')).render();
        return this;
    },

    _saveSettings: function (settings) {
        restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            events.trigger('g:localCheckout.settingsChanged');
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-local-checkout-error-message').text(
                resp.responseJSON.message);
        });
    }
});

export default ConfigView;
