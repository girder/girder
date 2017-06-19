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

            if (this.$('.g-configure-json-tasks-tab').hasClass('active')) {
                this._submitJson();
            } else {
                this._submitSlicerCli();
            }
        }
    },

    initialize: function () {
        this.isFolder = this.model.get('_modelType') === 'folder';
        this.resourceName = this.isFolder ? 'folder' : 'item';
    },

    render: function () {
        // For items, get current settings to pre-populate dialog
        let currentImage = null;
        let currentTaskName = null;
        let currentSlicerCliArgs = null;
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
        }

        this.$el.html(template({
            model: this.model,
            isFolder: this.isFolder,
            currentImage: currentImage,
            currentTaskName: currentTaskName,
            currentSlicerCliArgs
        })).girderModal(this);

        // Clear validation error message when switching tabs
        this.$('a[data-toggle="tab"]')
            .on('hide.bs.tab', (e) => {
                this.$('.g-validation-failed-message').text('');
            });
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
            path: `${this.resourceName}/${this.model.id}/item_task_json_description`,
            type: 'POST',
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
            path: `${this.resourceName}/${this.model.id}/item_task_slicer_cli_description`,
            type: 'POST',
            data,
            error: null
        }).done((job) => {
            router.navigate(`job/${job._id}`, {trigger: true});
        }).fail((resp) => {
            this.$('.g-validation-failed-message').text(resp.responseJSON.message);
        });
    }
});

export default ConfigureTasksDialog;
