import _ from 'underscore';

import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';
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
                    this.$('.g-sizeValue[model=user]').val(),
                    this.$('.g-sizeUnits[model=user]').val())
            }, {
                key: 'user_quota.default_collection_quota',
                value: valueAndUnitsToSize(
                    this.$('.g-sizeValue[model=collection]').val(),
                    this.$('.g-sizeUnits[model=collection]').val())
            }]);
        }
    },
    initialize: function () {
        restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['user_quota.default_user_quota',
                'user_quota.default_collection_quota'])
            }
        }).done(_.bind(function (resp) {
            this.settings = resp;
            this.render();
        }, this));
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
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-user-quota-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

export default ConfigView;
