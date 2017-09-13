girderTest.importPlugin('jobs');
girderTest.importPlugin('worker');
girderTest.startApp();

$(function () {
    describe('Unit test job details widget (should have cancel button).', function () {
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
                handler: 'worker_handler',
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
                expect($('button.g-job-cancel').length).toBe(1);

                girder.utilities.eventStream.trigger('g:event.job_status', {
                    data: {
                        _id: 'foo',
                        status: girder.plugins.jobs.JobStatus.SUCCESS
                    }
                });

                expect($('.g-job-status-badge').text()).toContain('Success');
                expect($('button.g-job-cancel').length).toBe(0);
            });

            runs(function () {
                girder.plugins.jobs.models.JobModel.prototype.fetch.andCallThrough();
                // Return to the main page, since 'job/foo' isn't legal without mocking
                girder.router.navigate('', {trigger: true});
            });
            girderTest.waitForLoad();
        });
    });
});
