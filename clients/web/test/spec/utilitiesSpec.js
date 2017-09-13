girderTest.startApp();

describe('Test EventStream', function () {
    it('test heartbeat', function () {
        var es = girder.utilities.eventStream,
            start = 0,
            stop = 0,
            close = 0;
        runs(function () {
            es.on('g:eventStream.stop', function () {
                stop += 1;
            });
            es.on('g:eventStream.start', function () {
                start += 1;
            });
            es.on('g:eventStream.close', function () {
                close += 1;
            });
            es.settings._heartbeatTimeout = 1;
            start = stop = close = 0;
            es.open();
        }, 'start event stream and set it to have a short timeout');
        waitsFor(function () {
            return stop >= 1;
        }, 'event stream heartbest to stop');
        runs(function () {
            expect(stop).toBeGreaterThan(0);
            es.settings._heartbeatTimeout = 5000;
        }, 'restart heartbeat');
        waitsFor(function () {
            // once for the initial start, once for the restart
            return start >= 2;
        }, 'restart to occur');
        runs(function () {
            expect(start).toBeGreaterThan(0);
            es.close();
        }, 'close stream');
        waitsFor(function () {
            return close >= 1;
        }, 'close to occur');
        runs(function () {
            expect(close).toBeGreaterThan(0);
        }, 'check if close was triggered');
    });
});
