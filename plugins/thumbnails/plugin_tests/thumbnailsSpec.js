girderTest.addCoveredScripts([
    '/static/built/plugins/thumbnails/templates.js',
    '/plugins/thumbnails/web_client/js/setup.js',
    '/plugins/thumbnails/web_client/js/ThumbnailModel.js',
    '/plugins/thumbnails/web_client/js/CreateThumbnailView.js',
    '/plugins/thumbnails/web_client/js/FlowView.js'
]);

girderTest.importStylesheet(
    '/static/built/plugins/thumbnails/plugin.min.css'
);

girder.events.trigger('g:appload.before');
new girder.App({
    el: 'body',
    parentView: null
});
girder.events.trigger('g:appload.after');

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

        runs(function () {
            $('a.g-folder-list-link:last').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Public' &&
                   $('.g-empty-parent-message:visible').length === 1;
        }, 'descending into Public folder');

        girderTest.binaryUpload('clients/web/static/img/Girder_Mark.png');

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
