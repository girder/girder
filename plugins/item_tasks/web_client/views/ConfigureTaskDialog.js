import { restRequest } from 'girder/rest';
import router from 'girder/router';
import View from 'girder/views/View';
import template from '../templates/configureTask.pug';
import 'girder/utilities/jquery/girderModal';

var ConfigureTaskDialog = View.extend({
    events: {
        'submit .g-slicer-cli-docker-form': function (e) {
            e.preventDefault();
            this.$('.g-validation-failed-message').empty();

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
            }).error((resp) => {
                this.$('.g-validation-failed-message').text(resp.responseJSON.message);
            });
        }
    },

    render: function () {
        var meta = this.model.get('meta') || {};
        var currentArgs = meta.itemTaskSlicerCliArgs;

        if (currentArgs) {
            try {
                currentArgs = JSON.stringify(currentArgs);
            } catch (e) {
                currentArgs = null;
            }
        }
        this.$el.html(template({
            item: this.model,
            currentImage: meta.itemTaskSpec && meta.itemTaskSpec.docker_image,
            currentArgs
        })).girderModal(this);
    }
});

export default ConfigureTaskDialog;
