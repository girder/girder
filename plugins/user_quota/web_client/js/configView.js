/**
 * Show the default quota settings for users and collections.
 */
girder.views.userQuota_ConfigView = girder.View.extend({
    events: {
        'submit #g-user-quota-form': function (event) {
            event.preventDefault();
            this.$('#g-user-quota-error-message').empty();
            this._saveSettings([{
                key: 'user_quota.default_user_quota',
                value: girder.userQuota.valueAndUnitsToSize(
                    this.$('.g-sizeValue[model=user]').val(),
                    this.$('.g-sizeUnits[model=user]').val())
            }, {
                key: 'user_quota.default_collection_quota',
                value: girder.userQuota.valueAndUnitsToSize(
                    this.$('.g-sizeValue[model=collection]').val(),
                    this.$('.g-sizeUnits[model=collection]').val())
            }]);
        }
    },
    initialize: function () {
        girder.restRequest({
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
        var userSizeInfo = girder.userQuota.sizeToValueAndUnits(
            this.settings['user_quota.default_user_quota']);
        var collectionSizeInfo = girder.userQuota.sizeToValueAndUnits(
            this.settings['user_quota.default_collection_quota']);
        this.$el.html(girder.templates.userQuotaConfig({resources: {
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
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'User and collection quotas and policies',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _saveSettings: function (settings) {
        girder.restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            girder.events.trigger('g:alert', {
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

girder.router.route(
    'plugins/user_quota/config', 'userQuotaConfig', function () {
        girder.events.trigger('g:navigateTo',
                              girder.views.userQuota_ConfigView);
    });

girder.exposePluginConfig('user_quota', 'plugins/user_quota/config');
