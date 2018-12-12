girderTest.importPlugin('thumbnails');
girderTest.startApp();

describe('Test the thumbnail creation UI.', function () {
    it('register a user', girderTest.createUser(
        'johndoe', 'john.doe@email.com', 'John', 'Doe', 'password!'
    ));

    it('uploads the thumbnail', function () {
        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(0);
            $('.g-user-text>a:first').click();
        });
        girderTest.waitForLoad();

        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(1);
            $('a.g-my-folders').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            // The page may be loaded, but the folder list still populates asynchronously
            return $('.g-folder-list>.g-folder-list-entry').length === 2;
        });

        runs(function () {
            $('a.g-folder-list-link:last').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Public' &&
                   $('.g-empty-parent-message:visible').length === 1;
        }, 'descending into Public folder');

        girderTest.binaryUpload('girder/web_client/src/assets/Girder_Mark.png');

        runs(function () {
            $('.g-item-list-link:first').click();
        });

        waitsFor(function () {
            return $('.g-file-actions-container .g-create-thumbnail').length === 1;
        }, 'the create thumbnail button to appear');

        runs(function () {
            $('.g-create-thumbnail').click();
        });

        waitsFor(function () {
            return $('input#g-thumbnail-width').length === 1;
        }, 'create thumbnail dialog to appear');
        girderTest.waitForDialog();

        runs(function () {
            $('#g-thumbnail-width').val('64');
            $('.g-submit-create-thumbnail').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('.g-thumbnail-container').length === 1;
        }, 'thumbnail to appear on the item');
    });
});
