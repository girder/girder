import FolderModel from '@girder/core/models/FolderModel';
import MarkdownWidget from '@girder/core/views/widgets/MarkdownWidget';
import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import UploadWidget from '@girder/core/views/widgets/UploadWidget';
import events from '@girder/core/events';
import { restRequest, getApiRoot } from '@girder/core/rest';

import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';

const ConfigView = View.extend({
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
            },
            {
                key: 'homepage.logo',
                value: this.logoFileId
            }]);
        },

        'click #g-homepage-logo-reset': function (event) {
            this.logoFileId = null;
            this._updateLogoDisplay();
        }
    },

    initialize: function () {
        const currentSettingsRequest = restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify([
                    'homepage.markdown',
                    'homepage.header',
                    'homepage.subheader',
                    'homepage.welcome_text',
                    'homepage.logo'
                ])
            }
        })
            // Keep only the first argument
            .then((resp) => resp);
        const assetsRequest = restRequest({
            method: 'GET',
            url: 'homepage/assets'
        })
            // Keep only the first argument
            .then((resp) => resp);

        $.when(currentSettingsRequest, assetsRequest)
            .done((settings, assets) => {
                // Create sub-widgets
                this.editor = new MarkdownWidget({
                    prefix: 'homepage',
                    placeholder: 'Enter Markdown for the homepage',
                    parentView: this,
                    parent: new FolderModel({_id: assets['homepage.markdown']}),
                    enableUploads: true,
                    maxUploadSize: 1024 * 1024 * 10,
                    allowedExtensions: ['png', 'jpeg', 'jpg', 'gif']
                });
                this.welcomeText = new MarkdownWidget({
                    prefix: 'welcome',
                    placeholder: 'Enter Markdown to replace the welcome text.',
                    parentView: this,
                    parent: new FolderModel({_id: assets['homepage.welcome_text']}),
                    enableUploads: true,
                    maxUploadSize: 1024 * 1024 * 10,
                    allowedExtensions: ['png', 'jpeg', 'jpg', 'gif']
                });

                // Set current settings
                this.editor.text = settings['homepage.markdown'];
                this.header = settings['homepage.header'];
                this.subHeader = settings['homepage.subheader'];
                this.welcomeText.text = settings['homepage.welcome_text'];
                this.logoFileId = settings['homepage.logo'];

                this.logoUploader = new UploadWidget({
                    parent: new FolderModel({_id: assets['homepage.logo']}),
                    parentType: 'folder',
                    title: 'Homepage Logo',
                    modal: false,
                    multiFile: false,
                    parentView: this
                });
                this.listenTo(this.logoUploader, 'g:uploadFinished', (event) => {
                    this.logoFileId = event.files[0].id;
                    this._updateLogoDisplay();
                });

                this.render();
            });
    },

    _updateLogoDisplay: function () {
        let logoUrl;
        if (this.logoFileId) {
            logoUrl = `${getApiRoot()}/file/${this.logoFileId}/download?contentDisposition=inline`;
        } else {
            logoUrl = require('@girder/core/assets/Girder_Mark.png');
        }
        this.$('.g-homepage-logo-preview img').attr('src', logoUrl);
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            header: this.header || null,
            subHeader: this.subHeader || null,
            defaultHeader: 'Girder',
            defaultSubHeader: 'Data management platform'
        }));
        this.editor
            .setElement(this.$('.g-homepage-container'))
            .render();
        this.welcomeText
            .setElement(this.$('.g-homepage-welcome-text-container'))
            .render();

        this.logoUploader
            .render()
            .$el.appendTo(this.$('.g-homepage-logo-upload-container'));
        this._updateLogoDisplay();

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
        this.$('#g-homepage-error-message').text('');
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
            this.$('#g-homepage-error-message').text(
                resp.responseJSON.message
            );
        });
    }
});

export default ConfigView;
