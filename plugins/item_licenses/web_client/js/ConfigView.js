/**
* Administrative configuration view.
*/
girder.views.item_licenses_ConfigView = girder.View.extend({
    events: {
        'submit #g-item-licenses-settings-form': function (event) {
            event.preventDefault();

            this.$('#g-item-licenses-error-message').empty();

            this._saveSettings([{
                key: 'item_licenses.licenses',
                value: this.$('#g-item-licenses').val().trim()
            }]);
        },
        'click #g-item-licenses-defaults': function (event) {
            event.preventDefault();

            girder.restRequest({
                type: 'GET',
                path: 'item/licenses',
                data: {
                    'default': true
                }
            }).done(_.bind(function (resp) {
                this.licenses = resp;
                this.render();
            }, this));
        }
    },

    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['item_licenses.licenses'])
            }
        }).done(_.bind(function (resp) {
            this.licenses = resp['item_licenses.licenses'];
            this.render();
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.item_licenses_config({
            licenses: JSON.stringify(this.licenses, null, 4)
        }));

        this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
            pluginName: 'Item licenses',
            el: this.$('.g-config-breadcrumb-container'),
            parentView: this
        }).render();

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
                timeout: 3000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-item-licenses-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

girder.router.route('plugins/item_licenses/config', 'itemLicensesConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.item_licenses_ConfigView);
});
