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
            },
            {
                key: 'homepage.logo',
                value: this.logoUrl
            }]);
        },

        'change #g-homepage-logo': function (event) {
            var reader = new FileReader();
            reader.onload = () => {
                this.$('.g-preview-logo').attr({
                    'src': reader.result,
                    'width': '50px'
                });
                this.logoUrl = reader.result;
            };

            reader.readAsDataURL(event.target.files[0]);
            this.$('.g-preview-logo').removeClass('hidden');
            /* Clear the value of the hidden file input to avoid 'Chrome'
            to not triger the change event when the same image is set,
            this line fix a bug */
            this.$('#g-homepage-logo').val(null);
        },

        'click #g-homepage-default-logo-btn': function (event) {
            this.logoUrl = require('girder/assets/Girder_Mark.png');
            this.$('.g-preview-logo').attr({
                'src': this.logoUrl,
                'width': '50px'
            });

            this.$('.g-preview-logo').removeClass('hidden');
        },

        'click #g-homepage-upload-logo-btn': function () {
            this.$('#g-homepage-logo').click();
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
            this.logoUrl = resp['homepage.logo'];

            this.render();
        }, this));
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
        this.$('.g-preview-logo').attr({'src': this.logoUrl, 'width': '50px'});
        if (this.logoUrl !== null) {
            this.$('.g-preview-logo').removeClass('hidden');
        }

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
