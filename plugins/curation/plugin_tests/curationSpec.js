girderTest.addCoveredScripts([
    '/static/built/plugins/curation/templates.js',
    '/plugins/curation/web_client/js/setup.js',
]);

girderTest.importStylesheet(
    '/static/built/plugins/curation/plugin.min.css'
);

girderTest.startApp();

describe('Test the curation UI.', function () {
    it('register a user', girderTest.createUser(
        'johndoe', 'john.doe@email.com', 'John', 'Doe', 'password!'
    ));
});
