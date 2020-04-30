girderTest.importPlugin('readme');
girderTest.startApp();

describe('Test the readme UI', function () {
    it('register a user', girderTest.createUser(
        'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!'
    ));

    it('navigate to the user\'s Public folder', function () {
        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(0);
            $('.g-user-text>a').first().trigger('click');
        });
        girderTest.waitForLoad();

        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(1);
            $('a.g-my-folders').trigger('click');
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            // The page may be loaded, but the folder list still populates asynchronously
            return $('.g-folder-list>.g-folder-list-entry').length === 2;
        });

        runs(function () {
            $('a.g-folder-list-link').last().trigger('click');
        });
        girderTest.waitForLoad();
    });

    it('does not render the README when there is no README', function () {
        runs(function () {
            expect($('.g-widget-readme').length).toBe(0);
        });
    });

    it('upload README.md', function () {
        girderTest.testUpload('plugins/readme/plugin_tests/data/README.md');
        girderTest.waitForLoad();
    });

    it('renders the README', function () {
        waitsFor(function () {
            return $('.g-widget-readme').length === 1;
        });
        runs(function () {
            expect($('.g-widget-readme').length).toBe(1);
        });
    });
});
