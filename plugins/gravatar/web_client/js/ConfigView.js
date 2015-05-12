/**
* Administrative configuration view.
*/
girder.views.gravatar_ConfigView = girder.View.extend({
    events: {
        'submit #g-gravatar-settings-form': function (event) {
            event.preventDefault();
            this.$('#g-gravatar-error-message').empty();

            this._saveSettings([{
                key: 'gravatar.default_image',
                value: this.$('#gravatar.default_image').val().trim()
            }]);
        }
    },

    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['gravatar.default_image'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#gravatar.default_image').val(
                resp['gravatar.default_image']
            );
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.gravatar_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Gravatar portraits',
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
            this.$('#g-gravatar-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

girder.router.route('plugins/gravatar/config', 'gravatarConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.gravatar_ConfigView);
});
