/**
 * Start the girder backbone app.
 */
girderTest.startApp();

describe('Test setApiRoot() and setStaticRoot() functions', function () {
    it('Check for default values and mutation', function () {
        waitsFor(function () {
            return $('.g-frontpage-body').length > 0;
        });

        runs(function () {
            var host = 'http://localhost:30019';

            // Test the default values.
            expect(girder.rest.apiRoot).toBe(host + '/api/v1');
            expect(girder.rest.staticRoot).toBe(host + '/static');

            var apiRootVal = '/foo/bar/v2';
            girder.rest.setApiRoot(apiRootVal);
            expect(girder.rest.apiRoot).toBe(apiRootVal);

            var staticRootVal = 'dynamic';
            girder.rest.setStaticRoot(staticRootVal);
            expect(girder.rest.staticRoot).toBe(staticRootVal);
        });
    });
});
