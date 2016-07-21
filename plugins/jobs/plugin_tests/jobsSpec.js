import App from 'girder/app';
import { events, eventStream } from 'girder/events';

import JobDetailsWidget from '../web_client/views/JobDetailsWidget';
import JobListWidget from '../web_client/views/JobListWidget';
import JobModel from '../web_client/models/JobModel';
import JobStatus from '../web_client/JobStatus';

$(function () {
    /* Include the built version of the our templates.  This means that grunt
    * must be run to generate these before the test. */
    girderTest.addCoveredScripts([
        '/static/built/plugins/jobs/templates.js',
        '/plugins/jobs/web_client/js/misc.js',
        '/plugins/jobs/web_client/js/views/JobDetailsWidget.js',
        '/plugins/jobs/web_client/js/views/JobListWidget.js'
    ]);
    girderTest.importStylesheet(
        '/static/built/plugins/jobs/plugin.min.css'
    );

    events.trigger('g:appload.before');
    var app = new App({
        el: 'body',
        parentView: null
    });
    events.trigger('g:appload.after');

    describe('Unit test the job detail widget.', function () {
        it('Show a job detail widget.', function () {
            waitsFor('app to render', function () {
                return $('#g-app-body-container').length > 0;
            });

            runs(function () {
                var job = new JobModel({
                    _id: 'foo',
                    title: 'My batch job',
                    status: JobStatus.INACTIVE,
                    log: 'Hello world\ngoodbye world',
                    updated: '2015-01-12T12:00:12Z',
                    created: '2015-01-12T12:00:00Z',
                    when: '2015-01-12T12:00:00Z',
                    timestamps: [{
                        status: JobStatus.QUEUED,
                        time: '2015-01-12T12:00:02Z'
                    }, {
                        status: JobStatus.RUNNING,
                        time: '2015-01-12T12:00:03Z'
                    }, {
                        status: JobStatus.SUCCESS,
                        time: '2015-01-12T12:00:12Z'
                    }]
                });

                var widget = new JobDetailsWidget({
                    el: $('#g-app-body-container'),
                    job: job,
                    parentView: app
                }).render();

                expect($('.g-monospace-viewer[property="kwargs"]').length).toBe(0);
                expect($('.g-monospace-viewer[property="log"]').text()).toBe(job.get('log'));
                expect($('.g-job-info-value[property="_id"]').text()).toBe(job.get('_id'));
                expect($('.g-job-info-value[property="title"]').text()).toBe(job.get('title'));
                expect($('.g-job-info-value[property="when"]').text()).toContain('January 12, 2015');
                expect($('.g-job-status-badge').text()).toContain('Inactive');

                expect($('.g-timeline-segment').length).toBe(3);
                expect($('.g-timeline-point').length).toBe(4);
                expect($('.g-timeline-start-label').text()).toBe('0 s');
                expect($('.g-timeline-end-label').text()).toBe('12 s');
                expect($('.g-timeline-point')[3].className).toContain('g-job-color-success');

                // Make sure view change happens when notification is sent for this job
                eventStream.trigger('g:event.job_status', {
                    data: {
                        _id: 'foo',
                        status: JobStatus.SUCCESS,
                        log: 'log changed'
                    }
                });

                expect($('.g-job-status-badge').text()).toContain('Success');
                expect($('.g-monospace-viewer[property="log"]').text()).toBe('log changed');

                // Make sure view change only happens for the currently viewed job
                eventStream.trigger('g:event.job_status', {
                    data: {
                        _id: 'bar',
                        status: JobStatus.QUEUED,
                        log: 'should not appear'
                    }
                });

                expect($('.g-job-status-badge').text()).toContain('Success');
                expect($('.g-monospace-viewer[property="log"]').text()).toBe('log changed');
            });
        });
    });

    describe('Unit test the job list widget.', function () {
        it('Show a job list widget.', function () {
            var jobs, rows;

            runs(function () {
                jobs = _.map([1, 2, 3], function (i) {
                    return new JobModel({
                        _id: 'foo' + i,
                        title: 'My batch job ' + i,
                        status: i,
                        updated: '2015-01-12T12:00:0' + i,
                        created: '2015-01-12T12:00:0' + i,
                        when: '2015-01-12T12:00:0' + i
                    });
                });

                var widget = new JobListWidget({
                    el: $('#g-app-body-container'),
                    filter: {},
                    parentView: app
                }).render();

                expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);

                // Add the jobs to the collection
                widget.collection.add(jobs);
            });

            waitsFor(function () {
                return $('.g-jobs-list-table>tbody>tr').length === 3;
            }, 'job list to auto-reload when collection is updated')

            runs(function () {
                // Make sure we are in reverse chronological order
                rows = $('.g-jobs-list-table>tbody>tr');
                expect($(rows[0]).text()).toContain('My batch job 3');
                expect($(rows[0]).text()).toContain('Success');
                expect($(rows[1]).text()).toContain('My batch job 2');
                expect($(rows[1]).text()).toContain('Running');
                expect($(rows[2]).text()).toContain('My batch job 1');
                expect($(rows[2]).text()).toContain('Queued');

                // Simulate an SSE notification that changes a job status
                eventStream.trigger('g:event.job_status', {
                    data: _.extend({}, jobs[0].attributes, {
                        status: 4
                    })
                });
            });

            // Table row should update automatically
            waitsFor(function () {
                return $('td.g-job-status-cell', rows[2]).text() === 'Error';
            });
        });
    });
});
