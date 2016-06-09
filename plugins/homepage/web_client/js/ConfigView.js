/**
 * Administrative configuration view to configure the homepage markdown.
 */
girder.views.homepage_ConfigView = girder.View.extend({
    events: {
        'submit #g-homepage-form': function (event) {
            event.preventDefault();
            this._saveSettings([{
                key: 'homepage.markdown',
                value: this.editor.val()
            }]);
        }
    },

    initialize: function () {
        this.editor = new girder.views.MarkdownWidget({
            text: '',
            prefix: 'homepage',
            placeholder: 'Enter Markdown for the homepage',
            allowedExtensions: ['png', 'jpg', 'jpeg', 'gif'],
            enableUploads: false,
            parentView: this
        }).on('g:fileUploaded', function (args) {
            // this.trigger('g:fileUploaded', args);
        }, this);

        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['homepage.markdown'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.editor.val(resp['homepage.markdown']);
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.homepage_config());

        this.editor.setElement(
            this.$('.g-homepage-container')).render();

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Homepage',
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
            this.$('#g-homepage-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

girder.router.route('plugins/homepage/config', 'homepageConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.homepage_ConfigView);
});
