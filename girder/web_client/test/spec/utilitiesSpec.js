girderTest.startApp();

describe('Test EventStream', function () {
    var onEventStreamStart;
    var onEventStreamStop;
    var onEventStreamClose;
    var onVisibilityStateChangeSpy;

    it('test EventStream creation', function () {
        runs(function () {
            onEventStreamStart = jasmine.createSpy('onEventStreamStart');
            girder.utilities.eventStream.on('g:eventStream.start', onEventStreamStart);

            onEventStreamStop = jasmine.createSpy('onEventStreamStop');
            girder.utilities.eventStream.on('g:eventStream.stop', onEventStreamStop);

            onEventStreamClose = jasmine.createSpy('onEventStreamClose');
            girder.utilities.eventStream.on('g:eventStream.close', onEventStreamClose);

            onVisibilityStateChangeSpy = spyOn(girder.utilities.eventStream, '_onVisibilityStateChange');
        }, 'spy on EventStream');
        runs(girderTest.createUser('johndoe', 'john.doe@email.com', 'John', 'Doe', 'password!'),
            'login with a user');
        waitsFor(function () {
            return onEventStreamStart.wasCalled;
        }, 'EventStream to trigger start event');
    });

    afterEach(function () {
        // Spy behaviors will automatically be removed after each
        onVisibilityStateChangeSpy.andCallThrough();

        onEventStreamStart.reset();
        onEventStreamStop.reset();
        onEventStreamClose.reset();
    });

    // "document.visibilityState" cannot be mocked, so stop / start on page hide cannot be tested directly
    it('test EventStream auto-stop', function () {
        runs(function () {
            onVisibilityStateChangeSpy.andCallFake(function () {
                girder.utilities.eventStream._stop();
            });

            document.dispatchEvent(new CustomEvent('visibilitychange'));
        }, 'simulate hiding the page');
        waitsFor(function () {
            return onEventStreamStop.wasCalled;
        }, 'EventStream to trigger stop event');
        runs(function () {
            expect(onEventStreamClose).not.toHaveBeenCalled();
        }, 'EventStream should not be closed');
    });

    it('test EventStream auto-start', function () {
        runs(function () {
            onVisibilityStateChangeSpy.andCallFake(function () {
                girder.utilities.eventStream._start();
            });

            document.dispatchEvent(new CustomEvent('visibilitychange'));
        }, 'simulate showing the page');
        waitsFor(function () {
            return onEventStreamStart.wasCalled;
        }, 'EventStream to trigger start event');
    });

    it('test EventStream shutdown', function () {
        runs(function () {
            girder.utilities.eventStream.close();
        }, 'close EventStream');
        waitsFor(function () {
            return onEventStreamStop.wasCalled && onEventStreamClose.wasCalled;
        }, 'EventStream to trigger stop and close events');
    });
});
