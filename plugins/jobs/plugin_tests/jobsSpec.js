$(function () {
    /* Include the built version of the our templates.  This means that grunt
    * must be run to generate these before the test. */
    girderTest.addCoveredScripts([
        '/static/built/plugins/jobs/templates.js',
        '/plugins/jobs/web_client/js/misc.js',
        '/plugins/jobs/web_client/js/models/JobModel.js',
        '/plugins/jobs/web_client/js/views/JobDetailsWidget.js'
    ]);
    girderTest.importStylesheet(
        '/static/built/plugins/jobs/plugin.min.css'
    );

    girder.events.trigger('g:appload.before');
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after');

    describe('Unit test the job widget.', function () {
        it('Show a job detail widget.', function () {
            waitsFor('app to render', function () {
                return $('#g-app-body-container').length > 0;
            });

            runs(function () {
                var job = new girder.models.JobModel({
                    _id: 'foo',
                    title: 'My batch job',
                    status: girder.jobs_JobStatus.INACTIVE,
                    log: 'Hello world\ngoodbye world',
                    when: '2015-01-12T12:00:00'
                });

                var widget = new girder.views.jobs_JobDetailsWidget({
                    el: $('#g-app-body-container'),
                    job: job,
                    parentView: app
                }).render();

                expect($('.g-monospace-viewer[property="kwargs"]').length).toBe(0);
                expect($('.g-monospace-viewer[property="log"]').text()).toBe(job.get('log'));
                expect($('.g-job-info-value[property="_id"]').text()).toBe(job.get('_id'));
                expect($('.g-job-info-value[property="title"]').text()).toBe(job.get('title'));
                expect($('.g-job-info-value[property="when"]').text()).toContain('January 12, 2015');
                expect($('.g-job-status-badge').text()).toBe('Inactive');

                job.on('change', widget.render, widget);
                job.set('status', girder.jobs_JobStatus.SUCCESS);

                expect($('.g-job-status-badge').text()).toBe('Success');
            });
        });
    });
});
