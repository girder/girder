import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

import { valueAndUnitsToSize, sizeToValueAndUnits } from '../utilities/Conversions';
import ConfigViewTemplate from '../templates/configView.pug';

var ConfigView = View.extend({
    events: {
        'submit #g-user-quota-form': function (event) {
            event.preventDefault();
            this.$('#g-user-quota-error-message').empty();
            this._saveSettings([{
                key: 'user_quota.default_user_quota',
                value: valueAndUnitsToSize(
                    this.$('#g-user-quota-user-size-value').val(),
                    this.$('#g-user-quota-user-size-units').val())
            }, {
                key: 'user_quota.default_collection_quota',
                value: valueAndUnitsToSize(
                    this.$('#g-user-quota-collection-size-value').val(),
                    this.$('#g-user-quota-collection-size-units').val())
            }]);
        }
    },
    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify([
                    'user_quota.default_user_quota',
                    'user_quota.default_collection_quota'
                ])
            }
        }).done((resp) => {
            this.settings = resp;
            this.render();
        });
    },

    render: function () {
        var userSizeInfo = sizeToValueAndUnits(
            this.settings['user_quota.default_user_quota']);
        var collectionSizeInfo = sizeToValueAndUnits(
            this.settings['user_quota.default_collection_quota']);
        this.$el.html(ConfigViewTemplate({resources: {
            user: {
                model: 'user',
                name: 'User',
                sizeValue: userSizeInfo.sizeValue,
                sizeUnits: userSizeInfo.sizeUnits
            },
            collection: {
                model: 'collection',
                name: 'Collection',
                sizeValue: collectionSizeInfo.sizeValue,
                sizeUnits: collectionSizeInfo.sizeUnits
            }
        }}));
        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'User and collection quotas and policies',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

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
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-user-quota-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
