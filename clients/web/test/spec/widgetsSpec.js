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
        var errorCalled=0, onMessageError=0;

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
            var origOnMessage = girder.eventStream._eventSource.onmessage;
            girder.eventStream._eventSource.onmessage = function (e) {
                try {
                    origOnMessage(e);
                } catch (err) {
                    onMessageError += 1;
                }
            };
            var stream = girder.events._events['g:navigateTo'][0].ctx.progressListView.eventStream;
            stream.on('g:error', function () { errorCalled += 1; });
            stream.on('g:event.progress', function () {
                throw 'intentional error';
            });
            _setProgress('success', 0);
        });
        waitsFor(function () {
            return onMessageError == 1;
        }, 'bad progress callback to be tried');
        runs(function () {
            _setProgress('error', 0);
        });
        waitsFor(function () {
            return onMessageError == 2;
        }, 'bad progress callback to be tried again');
        runs(function () {
            expect(errorCalled).toBe(0);
        });

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

        /* There is a 5 second timeout for fading out the success message.  We
         * wait for 4% of the progress of the previous task, there should be
         * less than a second left to wait for the two previous success
         * messages to vanish (but the error message might still be around). */
        waitsFor(function () {
            return $('.g-progress-widget-container').length < 4;
        }, 'at least the first progress to be hidden');

        runs(function () {
            girder.restRequest({path: 'webclienttest/progress/stop',
                                type: 'PUT', async: false});
        });
    });
});
