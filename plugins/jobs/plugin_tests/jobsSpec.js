/* globals girderTest, describe, expect, it, runs, waitsFor  */

girderTest.addCoveredScripts([
    '/clients/web/static/built/plugins/jobs/plugin.min.js'
]);

girder.events.trigger('g:appload.before');
var app = new girder.views.App({
    el: 'body',
    parentView: null
});
girder.events.trigger('g:appload.after');

$(function () {
    describe('Unit test the job detail widget.', function () {
        it('Show a job detail widget.', function () {
            waitsFor('app to render', function () {
                return $('#g-app-body-container').length > 0;
            });

            runs(function () {
                var jobInfo = {
                    _id: 'foo',
                    title: 'My batch job',
                    status: girder.plugins.jobs.JobStatus.INACTIVE,
                    log: ['Hello world\n', 'goodbye world'],
                    updated: '2015-01-12T12:00:12Z',
                    created: '2015-01-12T12:00:00Z',
                    when: '2015-01-12T12:00:00Z',
                    timestamps: [{
                        status: girder.plugins.jobs.JobStatus.QUEUED,
                        time: '2015-01-12T12:00:02Z'
                    }, {
                        status: girder.plugins.jobs.JobStatus.RUNNING,
                        time: '2015-01-12T12:00:03Z'
                    }, {
                        status: girder.plugins.jobs.JobStatus.SUCCESS,
                        time: '2015-01-12T12:00:12Z'
                    }]
                };

                // mock fetch to simulate fetching a job
                var oldFetch = girder.plugins.jobs.models.JobModel.prototype.fetch;
                girder.plugins.jobs.models.JobModel.prototype.fetch = function () {
                    this.set(jobInfo);
                    this.trigger('g:fetched');
                };

                girder.router.navigate('job/foo', {trigger: true});
                girder.plugins.jobs.models.JobModel.prototype.fetch = oldFetch;

                expect($('.g-monospace-viewer[property="kwargs"]').length).toBe(0);
                expect($('.g-monospace-viewer[property="log"]').text()).toBe(jobInfo.log.join(''));
                expect($('.g-job-info-value[property="_id"]').text()).toBe(jobInfo._id);
                expect($('.g-job-info-value[property="title"]').text()).toBe(jobInfo.title);
                expect($('.g-job-info-value[property="when"]').text()).toContain('January 12, 2015');
                expect($('.g-job-status-badge').text()).toContain('Inactive');

                expect($('.g-timeline-segment').length).toBe(3);
                expect($('.g-timeline-point').length).toBe(4);
                expect($('.g-timeline-start-label').text()).toBe('0 s');
                expect($('.g-timeline-end-label').text()).toBe('12 s');
                expect($('.g-timeline-point')[3].className).toContain('g-job-color-success');

                // Make sure view change happens when notification is sent for this job
                girder.utilities.eventStream.trigger('g:event.job_status', {
                    data: {
                        _id: 'foo',
                        status: girder.plugins.jobs.JobStatus.SUCCESS
                    }
                });

                expect($('.g-job-status-badge').text()).toContain('Success');

                // Make sure view change only happens for the currently viewed job
                girder.utilities.eventStream.trigger('g:event.job_status', {
                    data: {
                        _id: 'bar',
                        status: girder.plugins.jobs.JobStatus.QUEUED
                    }
                });

                expect($('.g-job-status-badge').text()).toContain('Success');

                // Test log output events
                girder.utilities.eventStream.trigger('g:event.job_log', {
                    data: {
                        _id: 'foo',
                        overwrite: true,
                        text: 'overwritten log'
                    }
                });
                expect($('.g-monospace-viewer[property="log"]').text()).toBe('overwritten log');

                girder.utilities.eventStream.trigger('g:event.job_log', {
                    data: {
                        _id: 'foo',
                        overwrite: false,
                        text: '<script type="text/javascript">xss probe!</script>'
                    }
                });

                expect($('.g-monospace-viewer[property="log"]').text()).toBe(
                    'overwritten log<script type="text/javascript">xss probe!</script>');
            });
        });
    });

    describe('Unit test the job list widget.', function () {
        it('Show a job list widget.', function () {
            var jobs, rows;

            runs(function () {
                jobs = _.map([1, 2, 3], function (i) {
                    return new girder.plugins.jobs.models.JobModel({
                        _id: 'foo' + i,
                        title: 'My batch job ' + i,
                        status: i,
                        updated: '2015-01-12T12:00:0' + i,
                        created: '2015-01-12T12:00:0' + i,
                        when: '2015-01-12T12:00:0' + i
                    });
                });

                var widget = new girder.plugins.jobs.views.JobListWidget({
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
            }, 'job list to auto-reload when collection is updated');

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
                girder.utilities.eventStream.trigger('g:event.job_status', {
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
