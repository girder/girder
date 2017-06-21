girderTest.addScripts([
    '/clients/web/static/built/plugins/{{ cookiecutter.plugin_name }}/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    describe('{{ cookiecutter.plugin_name }} homepage test', function () {
        it('verifies greeting is added to homepage', function () {
            waitsFor(function () {
                return girder.rest.numberOutstandingRestRequests() === 0;
            }, 'rest requests to finish');

            runs(function () {
                expect($('#g-app-body-container').find('p:contains("Hi from {{ cookiecutter.plugin_nice_name }}")').length).toBe(1);
            });
        });
    });
});
