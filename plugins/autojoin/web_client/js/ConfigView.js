/**
 * Administrative configuration view to configure the auto join settings.
 */
girder.views.autojoin_ConfigView = girder.View.extend({
    events: {
        'submit #g-autojoin-form': function (event) {
            event.preventDefault();
            this._saveSettings([{
                key: 'autojoin.markdown',
                value: this.editor.val()
            }]);
        }
    },

    initialize: function () {
        this.editor = new girder.views.MarkdownWidget({
            prefix: 'autojoin',
            placeholder: 'Enter Markdown for the autojoin',
            enableUploads: false,
            parentView: this
        });

        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['autojoin.markdown'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.editor.val(resp['autojoin.markdown']);
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.autojoin_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Auto Join',
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
            this.$('#g-autojoin-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

girder.router.route('plugins/autojoin/config', 'autojoinConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.autojoin_ConfigView);
});
