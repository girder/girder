import _ from 'underscore';

import FolderModel from 'girder/models/FolderModel';
import MarkdownWidget from 'girder/views/widgets/MarkdownWidget';
import PluginConfigBreadcrumbWidget from 'girder/views/widgets/PluginConfigBreadcrumbWidget';
import View from 'girder/views/View';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

var ConfigView = View.extend({
    events: {
        'submit #g-homepage-form': function (event) {
            event.preventDefault();
            this._saveSettings([{
                key: 'homepage.markdown',
                value: this.editor.val()
            },
            {
                key: 'homepage.header',
                value: this.$('#g-homepage-header').val()
            },
            {
                key: 'homepage.subheader',
                value: this.$('#g-homepage-subheader').val()
            },
            {
                key: 'homepage.welcome_text',
                value: this.welcomeText.val()
            }
            /* {
                key: 'homepage.logo',
                value: this.logo.val()
            } */]);
        }
    },

    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'homepage/markdown'
        }).done(_.bind(function (resp) {
            this.folder = new FolderModel({_id: resp.folderId});
            this.editor = new MarkdownWidget({
                prefix: 'homepage',
                placeholder: 'Enter Markdown for the homepage',
                parentView: this,
                parent: this.folder,
                enableUploads: true,
                maxUploadSize: 1024 * 1024 * 10,
                allowedExtensions: ['png', 'jpeg', 'jpg', 'gif']
            });
            this.welcomeText = new MarkdownWidget({
                prefix: 'welcome',
                placeholder: 'Enter Markdown to replace the welcome text.',
                parentView: this,
                parent: this.folder,
                enableUploads: true,
                maxUploadSize: 1024 * 1024 * 10,
                allowedExtensions: ['png', 'jpeg', 'jpg', 'gif']
            });
            this.editor.text = resp['homepage.markdown'];
            this.header = resp['homepage.header'];
            this.subHeader = resp['homepage.subheader'];
            this.welcomeText.text = resp['homepage.welcome_text'];
            this.logo = resp['homepage.logo'];

            this.render();
        }, this));
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            header: this.header || null,
            subHeader: this.subHeader || null,
            logo: this.logo || null,
            defaultHeader: 'Girder',
            defaultSubHeader: 'Data management platform',
            defaultLogo: {src: 'girder/assets/Girder_Mark.png', width: '82'}
        }));
        this.editor.setElement(
            this.$('.g-homepage-container')).render();
        this.welcomeText.setElement(
            this.$('.g-welcome-text-container')).render();

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Homepage',
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
        }).done(_.bind(function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).fail(_.bind(function (resp) {
            this.$('#g-homepage-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
});

export default ConfigView;
