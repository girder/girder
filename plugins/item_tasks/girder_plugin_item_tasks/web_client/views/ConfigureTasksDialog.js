import Backbone from 'backbone';

import { restRequest } from 'girder/rest';
import router from 'girder/router';
import View from 'girder/views/View';
import '../stylesheets/configureTasks.styl';
import 'girder/utilities/jquery/girderModal';

import template from '../templates/configureTasks.pug';

/**
 * View to configure item tasks. Supports both populating a folder with tasks
 * and configuring an item with a task. In both cases, tabs are presented to
 * allow choosing between a JSON container and a Slicer CLI container.
 */
var ConfigureTasksDialog = View.extend({
    events: {
        'submit .g-configure-docker-form': function (e) {
            e.preventDefault();
            this.$('.g-validation-failed-message').empty();

            const tabPane = this.$('.tab-pane.active').prop('id');
            if (tabPane === 'g-configure-json-tasks-tab-content') {
                this._submitJson();
            } else if (tabPane === 'g-configure-slicer-cli-task-tab-content') {
                this._submitSlicerCli();
            } else if (tabPane === 'g-configure-celery-task-tab-content') {
                this._submitCelery();
            } else {
                // This should never happen, just in case, we log it to the console.
                throw new Error('Could not find active tab');
            }
        }
    },

    initialize: function () {
        this.isFolder = this.model.resourceName === 'folder';
        this.resourceName = this.isFolder ? 'folder' : 'item';
    },

    render: function () {
        // For items, get current settings to pre-populate dialog
        let currentImage = null;
        let currentTaskName = null;
        let currentSlicerCliArgs = null;
        let currentModulePath = null;
        if (!this.isFolder) {
            const meta = this.model.get('meta') || {};

            currentSlicerCliArgs = meta.itemTaskSlicerCliArgs;
            if (currentSlicerCliArgs) {
                try {
                    currentSlicerCliArgs = JSON.stringify(currentSlicerCliArgs);
                } catch (e) {
                    currentSlicerCliArgs = null;
                }
            }

            currentImage = meta.itemTaskSpec && meta.itemTaskSpec.docker_image;
            currentTaskName = meta.itemTaskName;
            currentModulePath = meta.itemTaskImport;
        }

        restRequest({
            url: 'item_task/extensions'
        }).done((extensions) => {
            this.$el.html(template({
                model: this.model,
                isFolder: this.isFolder,
                currentImage: currentImage,
                currentTaskName: currentTaskName,
                currentSlicerCliArgs,
                currentModulePath,
                extensions
            })).girderModal(this).on('shown.bs.modal', () => {
                this.$('input:first').focus();
            });
        });

        // Clear validation error message when switching tabs
        this.$('a[data-toggle="tab"]')
            .on('hide.bs.tab', (e) => {
                this.$('.g-validation-failed-message').text('');
            })
            .on('shown.bs.tab', (e) => {
                this.$($(e.currentTarget).attr('href') + ' input:first').focus();
            });

        return this;
    },

    _submitJson: function () {
        var image = this.$('.g-configure-docker-image').val().trim();
        var taskNameElem = this.$('.g-configure-task-name');
        var setNameElem = this.$('.g-configure-use-name');
        var setDescriptionElem = this.$('.g-configure-use-description');

        var data = {
            pullImage: this.$('.g-configure-docker-pull-image').is(':checked')
        };
        if (image) {
            data.image = image;
        }
        if (taskNameElem.length) {
            data.taskName = taskNameElem.val().trim();
        }
        if (setNameElem.length) {
            data.setName = setNameElem.is(':checked');
        }
        if (setDescriptionElem.length) {
            data.setDescription = setDescriptionElem.is(':checked');
        }

        restRequest({
            url: `${this.resourceName}/${this.model.id}/item_task_json_description`,
            method: 'POST',
            data,
            error: null
        }).done((job) => {
            router.navigate(`job/${job._id}`, {trigger: true});
        }).fail((resp) => {
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    },

    _submitSlicerCli: function () {
        var image = this.$('.g-slicer-cli-docker-image').val().trim();
        var args = this.$('.g-slicer-cli-docker-args').val().trim();
        var setNameElem = this.$('.g-slicer-cli-use-name');
        var setDescriptionElem = this.$('.g-slicer-cli-use-description');

        var data = {
            pullImage: this.$('.g-slicer-cli-pull-image').is(':checked')
        };
        if (image) {
            data.image = image;
        }
        if (args) {
            data.args = args;
        }
        if (setNameElem.length) {
            data.setName = setNameElem.is(':checked');
        }
        if (setDescriptionElem.length) {
            data.setDescription = setDescriptionElem.is(':checked');
        }

        restRequest({
            url: `${this.resourceName}/${this.model.id}/item_task_slicer_cli_description`,
            method: 'POST',
            data,
            error: null
        }).done((job) => {
            router.navigate(`job/${job._id}`, {trigger: true});
        }).fail((resp) => {
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    },

    _submitCelery: function () {
        const extensionName = this.$('.g-worker-extension').val();
        const modulePath = this.$('.g-celery-import-path').val();
        const setNameElem = this.$('.g-configure-celery-use-name');
        const setDescriptionElem = this.$('.g-configure-celery-use-description');
        const data = {};

        if (this.resourceName === 'item') {
            if (!modulePath) {
                this.$('.g-validation-failed-message').text('Please enter a valid import path');
                return;
            }
            data.taskName = modulePath.trim();
        } else {
            data.extension = extensionName.trim();
        }

        if (setNameElem.length) {
            data.setName = setNameElem.is(':checked');
        }
        if (setDescriptionElem.length) {
            data.setDescription = setDescriptionElem.is(':checked');
        }

        restRequest({
            url: `${this.resourceName}/${this.model.id}/item_task_celery`,
            type: 'POST',
            data: data,
            error: null
        }).done(() => {
            // Here we want to reload the current view.  We have to unset the
            // history fragment otherwise backbone router just returns as a
            // no-op.  Ideally, we could just run fetch on the parent model
            // (for items) or collection (for folders) and the hierarchy view
            // would rerender automatically.  This seems to work for the item
            // view, but not the folder list view.
            Backbone.history.fragment = null;
            router.navigate(`${this.resourceName}/${this.model.id}`, {trigger: true, replace: true});
        }).fail((resp) => {
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    }
});

export default ConfigureTasksDialog;
