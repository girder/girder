girderTest.importPlugin('authorized_upload');
girderTest.startApp();

var secureUrl = null;
describe('Create an authorized upload.', function () {
    it('register a user', girderTest.createUser(
        'admin', 'admin@email.com', 'Admin', 'Admin', 'passwd'));

    it('go to the authorize upload page', function () {
        runs(function () {
            $('.g-user-text>a:first').click();
        });
        girderTest.waitForLoad();
        runs(function () {
            $('a.g-my-folders').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            // Wait for folders to show, and also the folder count
            return $('li.g-folder-list-entry').length > 0 &&
                $('.g-subfolder-count').text() === '2';
        }, 'my folders list to display');

        runs(function () {
            $('a.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Private' &&
                $('.g-empty-parent-message:visible').length === 1;
        }, 'descending into Private folder');

        runs(function () {
            $('.g-folder-actions-button').click();
            expect($('.g-folder-actions-menu li>a.g-authorize-upload-here').length).toBeGreaterThan(0);
            window.location.assign($('.g-authorize-upload-here').attr('href'));
        });

        waitsFor(function () {
            return $('btn.g-create-authorized-upload').length > 0;
        }, 'authorize upload page to display');
    });

    it('create an authorized upload', function () {
        runs(function () {
            $('btn.g-create-authorized-upload').click();
        });

        waitsFor(function () {
            return $('.g-url-container').is(':visible');
        }, 'secure URL to be displayed');

        runs(function () {
            secureUrl = $('.g-authorized-upload-url-target').val();
            expect(secureUrl).toMatch(/.*#authorized_upload\/[a-f0-9]+\/[a-zA-Z0-9]/);
        });
    });

    it('logout', girderTest.logout());
});

describe('Perform authorized upload', function () {
    it('go to the authorized upload URL', function () {
        var hash = secureUrl.substring(secureUrl.indexOf('#'));
        window.location.assign(hash);

        waitsFor(function () {
            return $('.g-authorized-upload-page-wrapper').length > 0;
        }, 'authorized upload page to display');

        runs(function () {
            girderTest._prepareTestUpload();
            girderTest.sendFile('girder/web_client/test/testFile.txt');
            $('#g-files').parent().addClass('hide');
            $('.g-start-upload').click();
        });

        waitsFor(function () {
            return $('.g-complete-wrapper:visible').length > 0;
        }, 'upload completion message to appear');

        runs(function () {
            window.callPhantom({
                action: 'uploadCleanup',
                suffix: girderTest._uploadSuffix
            });
        });
    });
});
