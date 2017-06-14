import { restRequest } from 'girder/rest';
import router from 'girder/router';
import View from 'girder/views/View';
import 'girder/utilities/jquery/girderModal';

import template from '../templates/configureTasks.pug';

var ConfigureTasksDialog = View.extend({
    events: {
        'submit .g-configure-docker-form': function (e) {
            e.preventDefault();
            this.$('.g-validation-failed-message').empty();

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
        }
    },

    render: function () {
        this.$el.html(template({
            folder: this.model
        })).girderModal(this);
    }
});

export default ConfigureTasksDialog;
