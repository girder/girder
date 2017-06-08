import { restRequest } from 'girder/rest';
import router from 'girder/router';
import View from 'girder/views/View';
import '../stylesheets/configureTasks.styl';
import 'girder/utilities/jquery/girderModal';

import template from '../templates/configureTasks.pug';

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

    render: function () {
        // For items, get current settings to pre-populate dialog
        let currentImage = null;
        let currentSlicerCliArgs = null;
        const isFolder = this.model.get('_modelType') === 'folder';
        if (!isFolder) {
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
        }

        this.$el.html(template({
            model: this.model,
            isFolder: isFolder,
            currentImage: currentImage,
            currentSlicerCliArgs
        })).girderModal(this);
    },

    _submitJson: function () {
        var image = this.$('.g-configure-docker-image').val().trim();
        var data = {
            pullImage: this.$('.g-configure-docker-pull-image').is(':checked')
        };
        if (image) {
            data.image = image;
        }

        restRequest({
            path: `item_task/${this.model.id}/json_description`,
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

        var data = {
            setName: this.$('.g-slicer-cli-use-name').is(':checked'),
            setDescription: this.$('.g-slicer-cli-use-description').is(':checked'),
            pullImage: this.$('.g-slicer-cli-pull-image').is(':checked')
        };

        if (image) {
            data.image = image;
        }
        if (args) {
            data.args = args;
        }

        restRequest({
            path: `item_task/${this.model.id}/slicer_cli_description`,
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
