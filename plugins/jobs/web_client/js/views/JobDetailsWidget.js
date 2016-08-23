girder.views.jobs_JobDetailsWidget = girder.View.extend({
    initialize: function (settings) {
        this.job = settings.job;

        girder.eventStream.on('g:event.job_status', function (event) {
            var info = event.data;
            if (info._id === this.job.id) {
                this.job.set(info);
                this.render();
            }
        }, this);

        girder.eventStream.on('g:event.job_log', function (event) {
            var info = event.data;
            if (info._id === this.job.id) {
                var container = this.$('.g-job-log-container');
                if (info.overwrite) {
                    this.job.set({log: [info.text]});
                    container.text(info.text);
                } else {
                    this.job.get('log').push(info.text);
                    container.append(_.escape(info.text));
                }
            }
        }, this);

        if (settings.renderImmediate) {
            this.render();
        }
    },

    render: function () {
        var status = this.job.get('status');
        this.$el.html(girder.templates.jobs_jobDetails({
            job: this.job,
            statusText: girder.jobs_JobStatus.text(status),
            colorClass: 'g-job-color-' + girder.jobs_JobStatus.classAffix(status),
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
                class: 'g-job-color-' + girder.jobs_JobStatus.classAffix(stamp.status)
            };
        }, this));

        var points = [{
            time: startTime,
            class: 'g-job-color-inactive',
            tooltip: 'Created at ' + new Date(startTime).toISOString()
        }];

        points = points.concat(_.map(timestamps, function (stamp) {
            var statusText = girder.jobs_JobStatus.text(stamp.status);
            return {
                time: stamp.time,
                tooltip: 'Moved to ' + statusText + ' at ' +
                         new Date(stamp.time).toISOString(),
                class: 'g-job-color-' + girder.jobs_JobStatus.classAffix(stamp.status)
            };
        }, this));

        var endTime = timestamps[timestamps.length - 1].time;
        var elapsed = (new Date(endTime) - new Date(startTime)) / 1000;

        new girder.views.TimelineWidget({
            el: this.$('.g-job-timeline-container'),
            parentView: this,
            points: points,
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
