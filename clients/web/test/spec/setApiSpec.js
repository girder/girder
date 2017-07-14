girderTest.startApp();

describe('Test setApiRoot() and setStaticRoot() functions', function () {
    it('Check for default values and mutation', function () {
        waitsFor(function () {
            return $('.g-frontpage-body').length > 0;
        });

        runs(function () {
            // Test the default values.
            expect(girder.rest.apiRoot.slice(girder.rest.apiRoot.indexOf('/', 7))).toBe('/api/v1');
            expect(girder.rest.staticRoot.slice(girder.rest.staticRoot.indexOf('/', 7))).toBe('/static');

            var apiRootVal = '/foo/bar/v2';
            girder.rest.setApiRoot(apiRootVal);
            expect(girder.rest.apiRoot).toBe(apiRootVal);

            var staticRootVal = 'dynamic';
            girder.rest.setStaticRoot(staticRootVal);
            expect(girder.rest.staticRoot).toBe(staticRootVal);
        });
    });
});
