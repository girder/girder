/* globals girderTest, describe, expect, it, runs, waitsFor  */

girderTest.addCoveredScripts([
    '/clients/web/static/built/plugins/jobs/plugin.min.js'
]);

girderTest.importStylesheet(
    '/static/built/plugins/jobs/plugin.min.css'
);

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

                girder.router.navigate('job/foo', { trigger: true });
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
            var jobs, rows, widget;

            girderTest.createUser(
                'admin', 'admin@email.com', 'Quota', 'Admin', 'testpassword')();

            runs(function () {
                widget = new girder.plugins.jobs.views.JobListWidget({
                    el: $('#g-app-body-container'),
                    filter: {},
                    parentView: app
                }).render();

                expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);
            });

            girderTest.waitForLoad();

            runs(function(){
                // Add the jobs to the collection
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

                widget.collection.add(jobs);
                widget.collection.trigger('g:changed');
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

        it('Job list widget filter by status & type.', function () {
            var jobs, rows, widget;
            runs(function () {
                widget = new girder.plugins.jobs.views.JobListWidget({
                    el: $('#g-app-body-container'),
                    filter: {},
                    parentView: app
                }).render();


                expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);

                //programmatically set value
                widget.typeFilterWidget.setValues({
                    'type A': true,
                    'type B': true,
                    'type C': false
                });

                //one item should be unchecked
                expect(
                    widget.$('.filter-container .type .dropdown ul li input[type="checkbox"]').toArray().reduce(function (total, input) {
                        return total + ($(input).is(':checked') ? 1 : 0);
                    }, 0)
                ).toBe(2);

                widget.$('.filter-container .type .dropdown ul li input').first().click();

                expect(
                    widget.$('.filter-container .type .dropdown ul li input[type="checkbox"]').toArray().reduce(function (total, input) {
                        return total + ($(input).is(':checked') ? 1 : 0);
                    }, 0)
                ).toBe(1);

                widget.$('.filter-container .type .dropdown input.g-job-filter-checkall').click();

                //all should be checked after clicking Check all
                expect(
                    widget.$('.filter-container .type .dropdown ul li input[type="checkbox"]').toArray().reduce(function (total, input) {
                        return total + ($(input).is(':checked') ? 1 : 0);
                    }, 0)
                ).toBe(3);
                expect($('.filter-container .type .dropdown input.g-job-filter-checkall').is(':checked')).toBe(true);

                widget.$('.filter-container .status .dropdown input.g-job-filter-checkall').click();

                expect(
                    widget.$('.filter-container .status .dropdown ul li input[type="checkbox"]').toArray().reduce(function (total, input) {
                        return total + ($(input).is(':checked') ? 1 : 0);
                    }, 0)
                ).toBe(0);

                widget.$('.g-page-size').val(50).trigger("change");
                expect(widget.pageSize).toBe(50);
            });
        });

        it('Trigger click event.', function () {
            var jobs, widget;

            runs(function () {
                widget = new girder.plugins.jobs.views.JobListWidget({
                    el: $('#g-app-body-container'),
                    parentView: app,
                    filter: {},
                    triggerJobClick: true
                }).render();

                expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);
            });

            girderTest.waitForLoad();

            runs(function(){
                // Add the jobs to the collection
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

                widget.collection.add(jobs);
                widget.collection.trigger('g:changed');
            });

            waitsFor(function () {
                return $('.g-jobs-list-table>tbody>tr').length === 3;
            }, 'job list to auto-reload when collection is updated');

            runs(function () {
                var fired = false;
                widget.on('g:jobClicked', function () {
                    fired = true;
                });
                widget.$('.g-job-trigger-link').click();
                expect(fired).toBe(true);
            });
        });

        it('job list widget in all jobs mode', function () {
            var jobs, widget;

            runs(function () {

                widget = new girder.plugins.jobs.views.JobListWidget({
                    el: $('#g-app-body-container'),
                    parentView: app,
                    filter: {},
                    allJobsMode: true
                });

                expect(widget.collection.resourceName).toEqual('job/all');

                girderTest.logout('logout from admin')();

                girderTest.createUser(
                    'user1', 'user@email.com', 'Quota', 'User', 'testpassword')();
            });

            girderTest.waitForLoad();

            runs(function () {
                widget = new girder.plugins.jobs.views.JobListWidget({
                    el: $('#g-app-body-container'),
                    parentView: app,
                    allJobsMode: true
                });
            });
            girderTest.waitForLoad();

            runs(function () {
                expect(widget.$('.g-jobs-list-table').length).toEqual(0);
            });
        });

        it('phase and time chart', function () {
            var jobs, rows, widget;
            runs(function () {
                widget = new girder.plugins.jobs.views.JobListWidget({
                    el: $('#g-app-body-container'),
                    filter: {},
                    parentView: app
                }).render();
            });

            girderTest.waitForLoad();

            runs(function () {
                jobs = _.map(['one', 'two', 'three'], function (t, i) {
                    return new girder.plugins.jobs.models.JobModel({
                        _id: 'foo' + i,
                        title: 'My batch job ' + i,
                        status: 4,
                        type: t,
                        timestamps: [
                            {
                                "status": 1,
                                "time": "2017-03-10T18:31:59.008Z"
                            },
                            {
                                "status": 2,
                                "time": "2017-03-10T18:32:06.190Z"
                            },
                            {
                                "status": 4,
                                "time": "2017-03-10T18:32:34.760Z"
                            }
                        ],
                        updated: '2017-03-10T18:32:34.760Z',
                        created: '2017-03-10T18:31:59.008Z',
                        when: '2017-03-10T18:31:59.008Z'
                    });
                });

                widget.collection.add(jobs);
                widget.collection.trigger('g:changed');

                $('.jobs.nav.nav-tabs li a[name="phase"]').tab('show');
            });

            waitsFor(function () {
                return widget.$('.g-jobs-graph svg .mark-rect.phase rect').length;
            }, "phase graph to render");

            runs(function () {
                $('.jobs.nav.nav-tabs li a[name="time"]').tab('show');
            })

            waitsFor(function () {
                return widget.$('.g-jobs-graph svg .mark-symbol.circle path').length;
            }, "time graph to render");

            runs(function () {
                $('.graph-filter-container .phase .dropdown input.g-job-filter-checkall').click();
            });

            waitsFor(function () {
                return !widget.$('.g-jobs-graph svg .mark-symbol.circle path').length;
            }, "graph to clear");
        });
    });
});
