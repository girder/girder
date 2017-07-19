girderTest.importPlugin('hashsum_download');
var app;
girderTest.startApp()
    .done(function (startedApp) {
        app = startedApp;
    });

describe('Unit test the file view augmentation', function () {
    var file;
    var sha512 = 'd9f804f8f7caceec12a1207c16c6b70cb1dbfd8ea8f48a36168c98898c' +
        '1f138a11e9d1b40769d3c112afb099c6be5d57fc1ee8cf353df91ca0d3cf5524ddb047';

    it('Create a file and its info dialog', function () {
        waitsFor('app to render', function () {
            return $('#g-app-body-container').length > 0;
        });

        runs(function () {
            file = new girder.models.FileModel({
                _id: 'fake_id',
                size: 12345,
                name: 'my_file.txt',
                sha512: sha512,
                mimeType: 'text/plain',
                created: '2016-06-28T14:58:59.235000+00:00'
            });

            new girder.views.widgets.FileInfoWidget({
                model: file,
                el: $('#g-dialog-container'),
                parentView: app
            }).render();
        });

        girderTest.waitForDialog();

        runs(function () {
            var container = $('.g-file-info-line[property="sha512"]');
            expect(container.length).toBe(1);
            expect($('input.g-hash-textbox', container).val()).toBe(sha512);
            expect($('a.g-keyfile-download', container).attr('href')).toBe(
                girder.rest.apiRoot + '/file/fake_id/hashsum_file/sha512'
            );
        });
    });
});

describe('Test configuration page', function () {
    it('register admin', girderTest.createUser(
        'admin', 'admin@email.com', 'John', 'Doe', 'password!'));

    it('navigate to config page', function () {
        window.location.assign('#plugins/hashsum_download/config');

        waitsFor(function () {
            return $('#g-hashsum-download-auto-compute').length > 0;
        }, 'config page to load');
    });

    it('update auto compute setting', function () {
        expect($('#g-hashsum-download-auto-compute').is(':checked')).toBe(false);
        $('#g-hashsum-download-auto-compute').click();
        $('.btn[value="Save"]').click();

        waitsFor(function () {
            return $('#g-alerts-container .alert-success').length > 0;
        }, 'saved alert to appear', 3000);
    });
});
