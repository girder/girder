girder.views.jobs_JobDetailsWidget = girder.View.extend({
    initialize: function (settings) {
        this.job = settings.job;
    },

    render: function () {
        this.$el.html(girder.templates.jobs_jobDetails({
            job: this.job,
            statusText: girder.jobs_JobStatus.text(this.job.get('status')),
            girder: girder
        }));
    }
});
