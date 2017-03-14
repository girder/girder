import View from 'girder/views/View';
import template from '../templates/jobDetails.pug';

var JobDetailsInfoView = View.extend({
    render: function () {
        this.$el.html(template({
            job: this.model
        }));
    }
});

export default JobDetailsInfoView;
