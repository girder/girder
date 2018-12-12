girderTest.importPlugin('jobs');
var app;
girderTest.startApp()
    .done(function (startedApp) {
        app = startedApp;
    });

describe('Unit test the job detail widget.', function () {
    it('Show a job detail widget.', function () {
        waitsFor('app to render', function () {
            return $('#g-app-body-container').length > 0;
        });

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

        runs(function () {
            // mock fetch to simulate fetching a job
            spyOn(girder.plugins.jobs.models.JobModel.prototype, 'fetch').andCallFake(function () {
                this.set(jobInfo);
                this.trigger('g:fetched');
                return $.Deferred().resolve(jobInfo).promise();
            });

            girder.router.navigate('job/foo', {trigger: true});
        });

        waitsFor(function () {
            return $('.g-job-info-key').length > 0;
        }, 'the JobDetailsWidget to finish rendering');

        runs(function () {
            expect($('.g-monospace-viewer[property="kwargs"]').length).toBe(0);
            expect($('.g-monospace-viewer[property="log"]').text()).toBe(jobInfo.log.join(''));
            expect($('.g-job-info-value[property="_id"]').text()).toBe(jobInfo._id);
            expect($('.g-job-info-value[property="title"]').text()).toBe(jobInfo.title);
            expect($('.g-job-info-value[property="when"]').text()).toContain('January 12, 2015');
            expect($('.g-job-status-badge').text()).toContain('Inactive');
            expect($('button.g-job-cancel').length).toBe(0);

            expect($('.g-timeline-segment').length).toBe(3);
            expect($('.g-timeline-point').length).toBe(4);
            expect($('.g-timeline-start-label').text()).toBe('0 s');
            expect($('.g-timeline-end-label').text()).toBe('12 s');

            function toHex(c) {
                var hex = parseInt(c, 10).toString(16);
                return hex.length === 1 ? '0' + hex : hex;
            }

            function rgbToHex(rgb) {
                rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
                return '#' + toHex(rgb[1]) + toHex(rgb[2]) + toHex(rgb[3]);
            }

            var backgroundColor = $('.g-timeline-point')[3].style.getPropertyValue('background-color');
            backgroundColor = rgbToHex(backgroundColor);
            var successColor = girder.plugins.jobs.JobStatus.color(girder.plugins.jobs.JobStatus.SUCCESS);
            expect(backgroundColor).toBe(successColor);

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
            // Test that if the event stream stops and starts, the status can
            // be updated.
            girder.utilities.eventStream.trigger('g:event.job_status', {
                data: {
                    _id: 'foo',
                    status: girder.plugins.jobs.JobStatus.QUEUED
                }
            });
            expect($('.g-job-status-badge').text()).toContain('Queued');
            jobInfo.status = girder.plugins.jobs.JobStatus.ERROR;
            // trigger event stream to start
            girder.utilities.eventStream.trigger('g:eventStream.start', {});
            expect($('.g-job-status-badge').text()).toContain('Error');
        });

        runs(function () {
            girder.plugins.jobs.models.JobModel.prototype.fetch.andCallThrough();
            // Return to the main page, since 'job/foo' isn't legal without mocking
            girder.router.navigate('', {trigger: true});
        });
        girderTest.waitForLoad();
    });
    it('finished value', function () {
        var jobs = _.map([
            girder.plugins.jobs.JobStatus.QUEUED,
            girder.plugins.jobs.JobStatus.RUNNING,
            girder.plugins.jobs.JobStatus.ERROR,
            girder.plugins.jobs.JobStatus.SUCCESS,
            girder.plugins.jobs.JobStatus.CANCELED
        ], function (status, i) {
            return new girder.plugins.jobs.models.JobModel({
                _id: 'foo' + i,
                title: 'My batch job ' + i,
                status: status,
                updated: '2015-01-12T12:00:0' + i,
                created: '2015-01-12T12:00:0' + i,
                when: '2015-01-12T12:00:0' + i
            });
        });
        var JobStatus = girder.plugins.jobs.JobStatus;
        expect(JobStatus.finished(jobs[0].get('status'))).toBe(false);
        expect(JobStatus.finished(jobs[1].get('status'))).toBe(false);
        expect(JobStatus.finished(jobs[2].get('status'))).toBe(true);
        expect(JobStatus.finished(jobs[3].get('status'))).toBe(true);
        expect(JobStatus.finished(jobs[4].get('status'))).toBe(true);
    });
});

describe('Unit test the job list widget.', function () {
    // This spy must be attached to the prototype, since the instantiation of JobListWidget will
    // bind and make calls to '_renderData' immediately
    var renderDataSpy;
    beforeEach(function () {
        renderDataSpy = spyOn(girder.plugins.jobs.views.JobListWidget.prototype, '_renderData').andCallThrough();
    });

    it('Show a job list widget.', function () {
        var jobs, rows, widget;

        girderTest.createUser(
            'admin', 'admin@email.com', 'Quota', 'Admin', 'testpassword')();

        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                filter: {},
                parentView: app,
                showGraphs: true,
                showFilters: true,
                showPageSizeSelector: true
            });
        });
        waitsFor(function () {
            // Wait for the pending fetch (causing the 2nd render) to complete, so it doesn't
            // overwrite "widget.collection" after the synchronous "widget.collection.add"
            // is made below
            return renderDataSpy.callCount >= 2;
        }, 'job list to finish initial loading');

        runs(function () {
            expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);

            jobs = _.map([
                girder.plugins.jobs.JobStatus.QUEUED,
                girder.plugins.jobs.JobStatus.RUNNING,
                girder.plugins.jobs.JobStatus.SUCCESS
            ], function (status, i) {
                return new girder.plugins.jobs.models.JobModel({
                    _id: 'foo' + i,
                    title: 'My batch job ' + i,
                    status: status,
                    updated: '2015-01-12T12:00:0' + i,
                    created: '2015-01-12T12:00:0' + i,
                    when: '2015-01-12T12:00:0' + i
                });
            });

            widget.collection.add(jobs);

            // job list should re-render when collection is updated
            expect($('.g-jobs-list-table>tbody>tr').length).toBe(3);
        });

        runs(function () {
            // Make sure we are in reverse chronological order
            rows = $('.g-jobs-list-table>tbody>tr');
            expect($(rows[0]).text()).toContain('My batch job 2');
            expect($(rows[0]).text()).toContain('Success');
            expect($(rows[1]).text()).toContain('My batch job 1');
            expect($(rows[1]).text()).toContain('Running');
            expect($(rows[2]).text()).toContain('My batch job 0');
            expect($(rows[2]).text()).toContain('Queued');

            // Simulate an SSE notification that changes a job status
            girder.utilities.eventStream.trigger('g:event.job_status', {
                data: _.extend({}, jobs[0].attributes, {
                    status: girder.plugins.jobs.JobStatus.ERROR
                })
            });
        });

        // Table row should update automatically
        waitsFor(function () {
            return $($('.g-jobs-list-table>tbody>tr').get(2)).find('td.g-job-status-cell').text() === 'Error';
        }, 'Third row status change to Error');

        runs(function () {
            // The data in this is meaningless, but this will trigger a new API fetch
            renderDataSpy.reset();
            girder.utilities.eventStream.trigger('g:event.job_created', {
                data: {
                    _id: 'foo' + 4,
                    title: 'My batch job ' + 4,
                    status: girder.plugins.jobs.JobStatus.ERROR,
                    updated: '2015-01-12T12:00:0' + 4,
                    created: '2015-01-12T12:00:0' + 4,
                    when: '2015-01-12T12:00:0' + 4
                }
            });
        });

        waitsFor(function () {
            return renderDataSpy.wasCalled;
        });

        runs(function () {
            // Since the server contains no actual jobs, once the API fetch completes, all of
            // the previously-added local jobs will be blown away, and the local view will
            // re-render to show no jobs
            expect($('.g-no-job-record').is(':visible')).toBe(true);
        });
    });

    it('Job list widget filter by status & type.', function () {
        var widget;
        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                filter: {},
                parentView: app,
                showGraphs: true,
                showFilters: true,
                showPageSizeSelector: true
            });
        });
        waitsFor(function () {
            return renderDataSpy.callCount >= 2;
        }, 'job list to finish initial loading');

        runs(function () {
            expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);

            // programmatically set value
            widget.typeFilterWidget.setItems({
                'type A': true,
                'type B': true,
                'type C': false
            });

            // one item should be unchecked
            expect(widget.$('.g-job-filter-container .type .dropdown ul li input[type="checkbox"]:checked').length).toBe(2);

            widget.$('.g-job-filter-container .type .dropdown ul li input').first().click();

            expect(widget.$('.g-job-filter-container .type .dropdown ul li input[type="checkbox"]:checked').length).toBe(1);

            widget.$('.g-job-filter-container .type .dropdown .g-job-checkall input').click();

            // all should be checked after clicking Check all
            expect(widget.$('.g-job-filter-container .type .dropdown ul li input[type="checkbox"]:checked').length).toBe(3);
            expect($('.g-job-filter-container .type .dropdown .g-job-checkall input').is(':checked')).toBe(true);

            widget.$('.g-job-filter-container .status .dropdown .g-job-checkall input').click();

            expect(widget.$('.g-job-filter-container .status .dropdown ul li input[type="checkbox"]:checked').length).toBe(0);

            widget.$('.g-page-size').val(50).trigger('change');
            expect(widget.collection.pageLimit).toBe(50);
        });
    });

    it('Trigger click event.', function () {
        var jobs, widget;

        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                parentView: app,
                filter: {},
                triggerJobClick: true,
                showGraphs: true,
                showFilters: true,
                showPageSizeSelector: true
            });
        });
        waitsFor(function () {
            return renderDataSpy.callCount >= 2;
        }, 'job list to finish initial loading');

        runs(function () {
            expect($('.g-jobs-list-table>tbody>tr').length).toBe(0);

            jobs = _.map([
                girder.plugins.jobs.JobStatus.QUEUED,
                girder.plugins.jobs.JobStatus.RUNNING,
                girder.plugins.jobs.JobStatus.SUCCESS
            ], function (status, i) {
                return new girder.plugins.jobs.models.JobModel({
                    _id: 'foo' + i,
                    title: 'My batch job ' + i,
                    status: status,
                    updated: '2015-01-12T12:00:0' + i,
                    created: '2015-01-12T12:00:0' + i,
                    when: '2015-01-12T12:00:0' + i
                });
            });

            widget.collection.add(jobs);
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
        var widget;
        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                parentView: app,
                filter: {},
                allJobsMode: true,
                showGraphs: true,
                showFilters: true,
                showPageSizeSelector: true
            });
        });
        waitsFor(function () {
            return renderDataSpy.callCount >= 2;
        }, 'job list to finish initial loading');

        runs(function () {
            expect(widget.collection.resourceName).toEqual('job/all');
        });
    });

    it('job list cancellation', function () {
        var jobs, widget;

        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                parentView: app,
                filter: {},
                triggerJobClick: true,
                showGraphs: true,
                showFilters: true,
                showPageSizeSelector: true
            }).render();
        });

        girderTest.waitForLoad();

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

            widget.collection.add(jobs);
        });

        waitsFor(function () {
            return $('.g-jobs-list-table>tbody>tr').length === 3;
        }, 'job list to auto-reload when collection is updated');

        runs(function () {
            // button is disabled when no job is checked
            expect(widget.$('.g-job-check-menu-button').is(':disabled')).toBe(true);

            widget.$('input:checkbox:not(:checked).g-job-checkbox').click();
            widget.$('input:checkbox:not(:checked).g-job-checkbox').click();
            widget.$('input:checkbox:not(:checked).g-job-checkbox').click();

            expect(widget.$('.g-job-check-menu-button').is(':disabled')).toBe(false);
            expect(widget.$('.g-job-checkbox-all').is(':checked')).toBe(true);
            widget.$('.g-job-checkbox-all').click();

            expect(widget.$('input:checkbox:not(:checked).g-job-checkbox').length).toBe(3);

            widget.$('.g-job-checkbox-all').click();
            expect(widget.$('input:checkbox:not(:checked).g-job-checkbox').length).toBe(0);

            widget.$('.g-jobs-list-cancel').click();
        });
    });

    it('timing history and time chart', function () {
        var jobs, widget;
        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                filter: {},
                parentView: app,
                showGraphs: true,
                showFilters: true,
                showPageSizeSelector: true
            });
        });
        waitsFor(function () {
            return renderDataSpy.callCount >= 2;
        }, 'job list to finish initial loading');

        runs(function () {
            jobs = _.map(['one', 'two', 'three'], function (type, i) {
                return new girder.plugins.jobs.models.JobModel({
                    _id: 'foo' + i,
                    title: 'My batch job ' + i,
                    status: girder.plugins.jobs.JobStatus.ERROR,
                    type: type,
                    timestamps: [
                        {
                            'status': girder.plugins.jobs.JobStatus.QUEUED,
                            'time': '2017-03-10T18:31:59.008Z'
                        },
                        {
                            'status': girder.plugins.jobs.JobStatus.RUNNING,
                            'time': '2017-03-10T18:32:06.190Z'
                        },
                        {
                            'status': girder.plugins.jobs.JobStatus.ERROR,
                            'time': '2017-03-10T18:32:34.760Z'
                        }
                    ],
                    updated: '2017-03-10T18:32:34.760Z',
                    created: '2017-03-10T18:31:59.008Z',
                    when: '2017-03-10T18:31:59.008Z'
                });
            });

            widget.collection.add(jobs);

            $('.g-jobs.nav.nav-tabs li a[name="timing-history"]').tab('show');
        });
        waitsFor(function () {
            // Charts will render asynchronously with Vega
            return widget.$('.g-jobs-graph svg .mark-rect.timing path').length;
        }, 'timing history graph to render');

        runs(function () {
            expect(widget.$('.g-jobs-graph svg .mark-rect.timing path').length).toBe(9);
            $('.g-jobs.nav.nav-tabs li a[name="time"]').tab('show');
        });
        waitsFor(function () {
            return widget.$('.g-jobs-graph svg .mark-symbol.circle path').length;
        }, 'time graph to render');

        runs(function () {
            expect(widget.$('.g-jobs-graph svg .mark-symbol.circle path').length).toBe(3);
            $('.g-job-filter-container .timing .dropdown .g-job-checkall input').click();
        });
        waitsFor(function () {
            return !widget.$('.g-jobs-graph svg .mark-symbol.circle path').length;
        }, 'graph to clear');
    });

    it('Instantiate without graphs, filter, and page size selector.', function () {
        var widget;

        runs(function () {
            widget = new girder.plugins.jobs.views.JobListWidget({
                el: $('#g-app-body-container'),
                parentView: app,
                filter: {}
            });
        });
        waitsFor(function () {
            return renderDataSpy.callCount >= 2;
        }, 'job list to finish initial loading');

        runs(function () {
            expect(widget.$('.g-jobs.nav.nav-tabs').length).toBe(0);
            expect(widget.$('.g-job-filter-container').length).toBe(0);
            expect(widget.$('.g-page-size-container').length).toBe(0);
        });
    });
});
