/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after');
});

function _setProgress(test, duration) {
    /* Set or update a current progress notification.
     *
     * :param test: test parameter to send to the webclienttest/progress
     *     endpoint
     * :param duration: duration to send to the endpoint
     */
    girder.restRequest({path: 'webclienttest/progress', type: 'GET',
                        data: {test: test, duration: duration}});
}

describe('Test widgets that are not covered elsewhere', function () {
    it('register a user',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('test task progress widget', function () {
        runs(function () {
            expect($('#g-app-progress-container:visible').length).toBe(0);
            _setProgress('success', 0);
        });
        waitsFor(function () {
            return $('.g-task-progress-title').text() == 'Progress Test';
        }, 'progress to be shown');
        waitsFor(function () {
            return $('.g-task-progress-message').text() == 'Done';
        }, 'progress to be complete');

        runs(function () {
            _setProgress('error', 0);
        });
        waitsFor(function () {
            return $('.g-task-progress-title:last').text() == 'Progress Test';
        }, 'progress to be shown');
        waitsFor(function () {
            return $('.g-task-progress-message:last').text() == 'Error: Progress error test.';
        }, 'progress to report an error');

        runs(function () {
            /* Ask for a long test, so that on slow machines we can still
             * detect a partial progress. */
            _setProgress('success', 100);
        });
        waitsFor(function () {
            return $('.g-task-progress-message:last').text() == 'Progress Message';
        }, 'progress to be shown');
        runs(function () {
            expect($('.g-progress-widget-container').length > 0);
        });
        waitsFor(function () {
            /* Wait until at least 4% has progressed, as it makes our
             * subsequent test not require an explicit wait */
            return parseFloat($('.progress-status .progress-percent:last').
                   text()) >= 4 && /left$/.test($(
                   '.progress-status .progress-left:last').text());
        }, 'progress to show estimated time');

        /* There is a five second timeout for fading out the success message.
         * Because we waiting for 4% of the progress of the previous task,
         * there should be less than a second left to wait for the first test
         * to vanish. */
        waitsFor(function () {
            return $('.g-progress-widget-container').length < 3;
        }, 'at least the first progress to be hidden');

        runs(function () {
            girder.restRequest({path: 'webclienttest/progress/stop',
                                type: 'PUT', async: false});
        });
    });
});
