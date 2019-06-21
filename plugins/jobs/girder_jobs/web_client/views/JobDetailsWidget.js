import _ from 'underscore';

import { restRequest } from '@girder/core/rest';
import TimelineWidget from '@girder/core/views/widgets/TimelineWidget';
import View from '@girder/core/views/View';
import eventStream from '@girder/core/utilities/EventStream';
import { formatDate, DATE_SECOND } from '@girder/core/misc';
import events from '@girder/core/events';

import JobDetailsWidgetTemplate from '../templates/jobDetailsWidget.pug';
import JobStatus from '../JobStatus';

import '../stylesheets/jobDetailsWidget.styl';

var JobDetailsWidget = View.extend({
    events: {
        'click .g-job-cancel': function (event) {
            this._cancelJob();
        }
    },
    initialize: function (settings) {
        this.job = settings.job;

        this.listenTo(eventStream, 'g:event.job_status', function (event) {
            var info = event.data;
            if (info._id === this.job.id) {
                this.job.set(info);
                this.render();
            }
        });

        this.listenTo(eventStream, 'g:event.job_log', function (event) {
            var info = event.data;
            if (info._id === this.job.id) {
                var container = this.$('.g-job-log-container');
                if (info.overwrite) {
                    this.job.set({ log: [info.text] });
                    container.text(info.text);
                } else {
                    this.job.get('log').push(info.text);
                    container.append(_.escape(info.text));
                }
            }
        });

        this.listenTo(eventStream, 'g:eventStream.start', function (event) {
            const status = this.job.get('status');
            if (!JobStatus.finished(status)) {
                this.job.fetch().done(() => { this.render(); });
            }
        });

        if (settings.renderImmediate) {
            this.render();
        }
    },

    render: function () {
        var status = this.job.get('status');
        this.$el.html(JobDetailsWidgetTemplate({
            job: this.job,
            statusText: JobStatus.text(status),
            textColor: JobStatus.textColor(status),
            color: JobStatus.color(status),
            JobStatus: JobStatus,
            formatDate: formatDate,
            DATE_SECOND: DATE_SECOND,
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
            color: JobStatus.color(JobStatus.INACTIVE),
            tooltip: 'Inactive: %r s'
        }];

        segments = segments.concat(_.map(timestamps.slice(0, -1), function (stamp, i) {
            var statusText = JobStatus.text(stamp.status);
            return {
                start: stamp.time,
                end: timestamps[i + 1].time,
                tooltip: statusText + ': %r s',
                color: JobStatus.color(stamp.status)
            };
        }, this));

        var points = [{
            time: startTime,
            color: JobStatus.color(JobStatus.INACTIVE),
            tooltip: 'Created at ' + new Date(startTime).toISOString()
        }];

        points = points.concat(_.map(timestamps, function (stamp) {
            var statusText = JobStatus.text(stamp.status);
            return {
                time: stamp.time,
                tooltip: 'Moved to ' + statusText + ' at ' +
                         new Date(stamp.time).toISOString(),
                color: JobStatus.color(stamp.status)
            };
        }, this));

        var endTime = timestamps[timestamps.length - 1].time;
        var elapsed = (new Date(endTime) - new Date(startTime)) / 1000;

        new TimelineWidget({
            el: this.$('.g-job-timeline-container'),
            parentView: this,
            points: points,
            segments: segments,
            startTime: startTime,
            endTime: endTime,
            startLabel: '0 s',
            endLabel: elapsed + ' s'
        }).render();
    },

    _cancelJob: function () {
        const jobId = this.job.id;
        restRequest({
            url: `job/${jobId}/cancel`,
            method: 'PUT',
            error: null
        }).done(() => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Job successfully canceled.',
                type: 'success',
                timeout: 4000
            });
        }).fail((err) => {
            events.trigger('g:alert', {
                icon: 'cancel',
                text: err,
                type: 'danger',
                timeout: 4000
            });
        });
    }
});

export default JobDetailsWidget;
