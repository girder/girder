girder.views.jobs_JobDetailsWidget = girder.View.extend({
    initialize: function (settings) {
        this.job = settings.job;
        this.job.on('change', this.render, this);

        girder.eventStream.on('g:event.job_status', function (event) {
            var job = event.data;
            if (job._id === this.job.id) {
                this.job.set(job);
            }
        }, this);

        if (settings.renderImmediate) {
            this.render();
        }
    },

    render: function () {
        this.$el.html(girder.templates.jobs_jobDetails({
            job: this.job,
            statusText: girder.jobs_JobStatus.text(this.job.get('status')),
            girder: girder,
            _: _
        }));

        this._renderTimelineWidget();

        return this;
    },

    _renderTimelineWidget: function () {
        var timestamps = this.job.get('timestamps');

        if (!timestamps || !timestamps.length) {
            return;
        }

        var startTime = this.job.get('created');
        var segments = [{
            start: startTime,
            end: timestamps[0].time,
            class: 'g-job-color-inactive',
            tooltip: 'Inactive: %r s'
        }];

        segments = segments.concat(_.map(timestamps.slice(0, -1), function (stamp, i) {
            var statusText = girder.jobs_JobStatus.text(stamp.status);
            return {
                start: stamp.time,
                end: timestamps[i + 1].time,
                tooltip: statusText + ': %r s',
                class: 'g-job-color-' + statusText.toLowerCase()
            };
        }, this));
        var endTime = timestamps[timestamps.length - 1].time;
        var elapsed = (new Date(endTime) - new Date(startTime)) / 1000;

        new girder.views.TimelineWidget({
            el: this.$('.g-job-timeline-container'),
            parentView: this,
            segments: segments,
            startTime: startTime,
            endTime: endTime,
            startLabel: '0 s',
            endLabel: elapsed + ' s'
        }).render();
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
