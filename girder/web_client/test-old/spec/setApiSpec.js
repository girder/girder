girderTest.startApp();

describe('Test setApiRoot() function', function () {
    it('Check for default values and mutation', function () {
        waitsFor(function () {
            return $('.g-frontpage-body').length > 0;
        });

        runs(function () {
            // Test the default values.
            expect(girder.rest.getApiRoot().slice(
                girder.rest.getApiRoot().indexOf('/', 7))).toBe('/api/v1');

            var apiRootVal = '/foo/bar/v2';
            girder.rest.setApiRoot(apiRootVal);
            expect(girder.rest.getApiRoot()).toBe(apiRootVal);
        });
    });
});
