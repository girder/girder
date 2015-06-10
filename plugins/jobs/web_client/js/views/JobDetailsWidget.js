girder.views.jobs_JobDetailsWidget = girder.View.extend({
    initialize: function (settings) {
        this.job = settings.job;

        if (settings.renderImmediate) {
            this.render();
        }
    },

    render: function () {
        this.$el.html(girder.templates.jobs_jobDetails({
            job: this.job,
            statusText: girder.jobs_JobStatus.text(this.job.get('status')),
            girder: girder
        }));

        return this;
    }
});

girder.router.route('job/:id', 'jobView', function (id) {
    var job = new girder.models.JobModel({_id: id}).once('g:fetched', function () {
        girder.events.trigger('g:navigateTo', girder.views.jobs_JobDetailsWidget, {
            job: job,
            renderImmediate: true
        });
    }, this).once('g:error', function () {
        girder.router.navigate('collections', {trigger: true});
    }, this).fetch();
});
