/**
 * This widget provides a text field that will search any set of data types
 * and show matching results as the user types. Results can be clicked,
 * triggering a callback.
 */
girder.views.provenance_ConfigView = girder.View.extend({
    events: {
        'submit #g-provenance-form': function (event) {
            event.preventDefault();
            this.$('#g-provenance-error-message').empty();

            this._saveSettings([{
                key: 'provenance.resources',
                value: this.$('#provenance.resources').val().trim()
            }]);
        }
    },
    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
                list: JSON.stringify(['provenance.resources'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#provenance.resources').val(
                resp['provenance.resources']
            );
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.provenance_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Provenance tracker',
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
            this.$('#g-provenance-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

girder.router.route('plugins/provenance/config', 'provenanceConfig', function () {
    girder.events.trigger('g:navigateTo', girder.views.provenance_ConfigView);
});

girder.exposePluginConfig('provenance', 'plugins/provenance/config');
