import View from 'girder/views/View';

import template from '../templates/jobDetails.pug';
import '../stylesheets/jobDetails.styl';

var JobDetailsInfoView = View.extend({
    render: function () {
        this.$el.html(template({
            job: this.model
        }));
        return this;
    }
});

export default JobDetailsInfoView;
