girderTest.importPlugin('backbone');
girderTest.addScript('/plugins/backbone/plugin_tests/helper.js');

describe('collection', function () {
    it('login', function () {
        testHelper.login();
    });
});
