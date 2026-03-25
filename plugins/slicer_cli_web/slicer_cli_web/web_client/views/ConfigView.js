import ConfigViewTemplate from '../templates/configView.pug';
import '../stylesheets/configView.styl';
import { showJobSuccessAlert } from './utils';

const $ = girder.$;
const View = girder.views.View;
const events = girder.events;
const restRequest = girder.rest.restRequest;
const BrowserWidget = girder.views.widgets.BrowserWidget;
const PluginConfigBreadcrumbWidget = girder.views.widgets.PluginConfigBreadcrumbWidget;

/**
 * Show the default quota settings for users and collections.
 */
const ConfigView = View.extend({
    events: {
        'submit #g-slicer-cli-web-form'(event) {
            event.preventDefault();
            this.$('#g-slicer-cli-web-error-message').empty();
            this._saveSettings([{
                key: 'slicer_cli_web.task_folder',
                value: this.$('#g-slicer-cli-web-upload-folder').val()
            }, {
                key: 'slicer_cli_web.worker_config_item',
                value: this.$('#g-slicer-cli-web-worker-config-item').val()
            }]);
        },
        'submit #g-slicer-cli-web-upload-form'(event) {
            event.preventDefault();
            this.$('#g-slicer-cli-web-error-upload-message').empty();
            this._uploadImage(
                $('#g-slicer-cli-web-image').val(),
                $('#g-slicer-cli-web-folder').val());
        },
        'click .g-open-browser': '_openBrowser',
        'click .g-open-local-browser': '_openLocalBrowser',
        'click .g-open-item-browser': '_openItemBrowser'
    },

    initialize() {
        this._browserWidgetView = new BrowserWidget({
            parentView: this,
            titleText: 'Task Upload Folder',
            helpText: 'Browse to a location to select it as the upload folder.',
            submitText: 'Select Folder',
            validate(model) {
                const isValid = $.Deferred();
                if (!model) {
                    isValid.reject('Please select a valid root.');
                } else if (model.get('_modelType') !== 'folder' && !this.showItems) {
                    isValid.reject('Please select a folder.');
                } else if (model.get('_modelType') !== 'item' && this.showItems) {
                    isValid.reject('Please select an item.');
                } else {
                    isValid.resolve();
                }
                return isValid.promise();
            },
            rootSelectorSettings: {
                pageLimit: 1000
            }
        });
        this.listenTo(this._browserWidgetView, 'g:saved', (val) => {
            this.$(this._destination).val(val.id);
            if (this._altdestination) {
                this.$(this._altdestination).val(val.id);
            }
        });

        ConfigView.getSettings().then((settings) => {
            this.settings = settings;
            this.render();
            return null;
        });
    },

    render() {
        this.$el.html(ConfigViewTemplate({
            settings: this.settings
        }));
        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Slicer CLI Web',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _uploadImage(imagename, folderid) {
        /* Now submit */
        const name = imagename.split(',').map((d) => d.trim()).filter((d) => d.length > 0);
        return restRequest({
            method: 'PUT',
            url: 'slicer_cli_web/docker_image',
            data: {
                name: JSON.stringify(name),
                folder: folderid
            },
            error: null
        }).done((job) => {
            showJobSuccessAlert(job);
        }).fail((resp) => {
            this.$('#g-slicer-cli-web-error-upload-message').text(
                resp.responseJSON.message
            );
        });
    },

    _openBrowser() {
        this._destination = '#g-slicer-cli-web-upload-folder';
        this._altdestination = '#g-slicer-cli-web-folder';
        this._browserWidgetView.titleText = 'Task Upload Folder';
        this._browserWidgetView.helpText = 'Browse to a location to select it as the upload folder.';
        this._browserWidgetView.submitText = 'Select Folder';
        this._browserWidgetView.showItems = false;
        this._browserWidgetView.selectItem = false;
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    },
    _openLocalBrowser() {
        this._destination = '#g-slicer-cli-web-folder';
        this._altdestination = null;
        this._browserWidgetView.titleText = 'Task Upload Folder';
        this._browserWidgetView.helpText = 'Browse to a location to select it as the upload folder.';
        this._browserWidgetView.submitText = 'Select Folder';
        this._browserWidgetView.showItems = false;
        this._browserWidgetView.selectItem = false;
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    },
    _openItemBrowser() {
        this._destination = '#g-slicer-cli-web-worker-config-item';
        this._altdestination = null;
        this._browserWidgetView.titleText = 'Worker Configuration Item';
        this._browserWidgetView.helpText = 'Select an item with a specification for worker management.';
        this._browserWidgetView.submitText = 'Select Item';
        this._browserWidgetView.showItems = true;
        this._browserWidgetView.selectItem = true;
        this._browserWidgetView.setElement($('#g-dialog-container')).render();
    },

    _saveSettings(settings) {
        /* Now save the settings */
        return restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            ConfigView.clearSettingsCache();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-slicer-cli-web-error-message').text(
                resp.responseJSON.message
            );
        });
    }
}, {
    clearSettingsCache() {
        delete ConfigView.settings;
    },
    getSettings() {
        if (ConfigView.settings) {
            return ConfigView.settings;
        }
        ConfigView.settings = restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify([
                    'slicer_cli_web.task_folder',
                    'slicer_cli_web.worker_config_item'
                ])
            }
        }).then((resp) => {
            const settings = {
                task_folder: resp['slicer_cli_web.task_folder'],
                worker_config_item: resp['slicer_cli_web.worker_config_item']
            };

            return settings;
        });
        return ConfigView.settings;
    }
});

export default ConfigView;
