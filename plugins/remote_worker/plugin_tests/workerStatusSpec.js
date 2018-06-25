girderTest.importPlugin('jobs');
girderTest.importPlugin('remote_worker');
girderTest.startApp();

describe('Unit test worker status page', function () {
    it('create the admin user', function () {
        girderTest.createUser(
            'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword')();
    });
    it('Go on the worker status page from the jobs view', function () {
        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]').length > 0;
        }, 'admin console link to load');
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-all-jobs').length > 0;
        }, 'the admin console to load');
        runs(function () {
            $('.g-all-jobs > a').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-job-worker-task-info').length > 0;
        }, 'the tasks information button to load');
        runs(function () {
            $('.g-job-worker-task-info').click();
        });
    });
    it('Check refresh button', function () {
        waitsFor(function () {
            return $('.g-worker-status-header').length > 0;
        }, 'the worker status page to load');
        runs(function () {
            expect($('.icon-spin4').length > 0);
        });
    });
});
