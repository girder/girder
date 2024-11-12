/* globals girderTest, describe, it, expect, waitsFor, runs */
girderTest.importPlugin('jobs', 'worker', 'slicer_cli_web');

var slicer;
girderTest.promise.done(function () {
    slicer = girder.plugins.slicer_cli_web;
});

girderTest.startApp();

// Creates container and Default Task Folder and sets it in the settings using REST
function createDefaultTaskFolder(name, description, folder) {
    var collectionID = false;
    runs(function () {
        var resp = girder.rest.restRequest({
            url: '/collection',
            method: 'POST',
            data: {
                name: name,
                description: description,
                public: true
            },
            async: false
        });
        collectionID = resp.responseJSON._id;
        return resp && resp.responseJSON;
    }, 'Creating Collection');

    var folderID = false;
    runs(function () {
        var resp = girder.rest.restRequest({
            url: '/folder',
            method: 'POST',
            data: {
                name: folder,
                parentType: 'collection',
                parentId: collectionID,
                public: true
            },
            async: false
        });
        folderID = resp.responseJSON._id;
        return resp && resp.responseJSON;
    }, 'Creating SubFolder');

    runs(function () {
        var resp = girder.rest.restRequest({
            url: '/system/setting',
            method: 'PUT',
            data: {
                key: 'slicer_cli_web.task_folder',
                value: folderID
            },
            async: false
        });
        return resp && resp.responseJSON;
    }, 'Setting Default Task Folder');
}

function navigateToCollectionsFolder(collectionName, folderName) {
    waitsFor(function () {
        return $('a.g-nav-link[g-target="collections"]').length > 0;
    }, 'collection list link to load');
    runs(function () {
        $('a.g-nav-link[g-target="collections"]').click();
    });
    waitsFor(function () {
        return $('.g-collection-create-button').length > 0;
    }, 'collection list screen to load');
    girderTest.waitForLoad();
    waitsFor(function () {
        return $('.g-collection-list-entry').length > 0;
    }, 'collection list to load');

    // NOTE: This is equivalent to indexOf, can have multiple matches
    runs(function () {
        $('.g-collection-link:contains(' + collectionName + ')').first().click();
    });
    girderTest.waitForLoad();

    waitsFor(function () {
        return $('.g-folder-list-link').length > 0;
    }, 'the folder list to load');
    runs(function () {
        $('.g-folder-list-link:contains(' + folderName + ')').first().click();
    });
    girderTest.waitForLoad();
}

describe('UploadDockerImages button and functionality', function () {
    it('login, setup collection/folder and navigate to it', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'password')();
        createDefaultTaskFolder('Tasks', 'Default Tasks', 'Slicer CLI Web Tasks');
        navigateToCollectionsFolder('Tasks', 'Slicer CLI Web Tasks');
    });

    it('check docker task image upload button', function () {
        waitsFor(function () {
            return ($('.g-upload-slicer-cli-task-button').length > 0);
        }, 'upload docker image button to be visible');
        runs(function () {
            expect($('.g-upload-slicer-cli-task-button').length > 0);
        });
    });

    it('test the upload docker image button', function () {
        runs(function () {
            $('.g-upload-slicer-cli-task-button').click();
        });
        waitsFor(function () {
            return ($('#g-slicer-cli-web-image').length > 0);
        });
        girderTest.waitForDialog();
        runs(function () {
            expect($('#g-slicer-cli-web-image').length > 0);
        }, 'the modal dialog to load');
        runs(function () {
            $('#g-slicer-cli-web-upload-form button.close').click();
        }, 'wait for dialog to close');
        girderTest.waitForLoad();
    });

    it('logout from admin account', girderTest.logout());
    it('register a (normal user)',
        girderTest.createUser('johndoe',
            'john.doe@girder.test',
            'John',
            'Doe',
            'password!'));
    it('navigate to task folder and check icon', function () {
        navigateToCollectionsFolder('Tasks', 'Slicer CLI Web Tasks');
        runs(function () {
            expect($('.g-upload-slicer-cli-task-button').length === 0);
        });
    });
});
