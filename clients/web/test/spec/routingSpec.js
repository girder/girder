/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

function _getFirstId(collection, ids, key, fetchParamsFunc)
{
    var coll;
    runs(function () {
        coll = new collection();
        var params;
        if (fetchParamsFunc)
            params = fetchParamsFunc(coll);
        coll.fetch(params);
    });
    waitsFor(function () {
        return coll.length > 0;
    }, 'collection to load');
    runs(function () {
        ids[key] = coll.first().get('_id');
    });
}

function _testRoute(route, hasDialog, testFunc)
/* Test going to a particular route, waiting for the dialog or page to load
 *  fully, and then testing that we have what we expect.
 * Enter: route: the hash url fragment to go to.
 *        hasDialog: true if we should wait for a dialog to appear.
 *        testFunc: a function with an expect call to validate the route.  If
 *                  this is not specified, jut navigate to the specified route.
 */
{
    runs(function() {
        window.location.hash = route;
    });
    /* We need to let the window have a chance to reload, so we just release
     * our time slice. */
    waits(1);
    if (hasDialog) {
        girderTest.waitForDialog('route: '+route);
    } else {
        girderTest.waitForLoad('route: '+route);
    }
    if (testFunc) {
        waitsFor(testFunc, 'route: '+route);
        runs(function () {
            expect(testFunc()).toBe(true);
        });
    }
}

describe('Test routing paths', function () {
    var ids = {};

    /* We need at least one of everything, so create that first */
    it('register a user',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));
    it('go to collections page', function () {
        runs(function () {
            $("a.g-nav-link[g-target='collections']").click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        }, 'navigate to collections page');

        runs(function () {
            expect($('.g-collection-list-entry').length).toBe(0);
        });
    });

    it('create a collection',
        girderTest.createCollection('Test Collection',
                                    'Collection Description'));
    it('make the collection public', function () {
        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');
        runs(function () {
            $('.g-collection-actions-button').click();
        });
        waitsFor(function () {
            return $(".g-collection-access-control[role='menuitem']:visible").length == 1;
        }, 'access control menu item to appear');
        runs(function () {
            $('.g-collection-access-control').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-dialog-container').hasClass('in') &&
                   $('#g-access-public:visible').is(':enabled');
        }, 'dialog and public access radio button to appear');
        runs(function () {
            $('#g-access-public').click();
        });
        waitsFor(function () {
            return $('.g-save-access-list:visible').is(':enabled') &&
                   $('.radio.g-selected').text().match("Public").length > 0;
        }, 'access save button to appear');
        runs(function () {
            $('.g-save-access-list').click();
        });
        girderTest.waitForLoad();
    });
    it('go to groups page', girderTest.goToGroupsPage());
    it('Create a public group',
        girderTest.createGroup('Public Group', 'public group', true));
    it('collect ids for tests', function () {
        _getFirstId(girder.collections.UserCollection, ids, 'admin');
        _getFirstId(girder.collections.CollectionCollection, ids, 'collection');
        _getFirstId(girder.collections.FolderCollection, ids,
                    'collectionFolder', function(){
            return {parentId: ids.collection, parentType: 'collection'};
        });
        _getFirstId(girder.collections.FolderCollection, ids, 'userFolder',
            function () {
            return {parentId: ids.admin, parentType: 'user'};
        });
        _getFirstId(girder.collections.GroupCollection, ids, 'group');
        _getFirstId(girder.collections.AssetstoreCollection, ids, 'assetstore');
    });
    it('create an item in the private folder of the user', function () {
        runs(function () {
            girder.restRequest({type:'POST', path:'file', data: {
                parentType: 'folder',
                parentId: ids.userFolder,
                name:'Link File',
                linkUrl: 'http://data.kitware.com'
            }, async: false});
        });
        _getFirstId(girder.collections.ItemCollection, ids, 'item',
            function () {
            return {folderId: ids.userFolder};
        });
        _getFirstId(girder.collections.ItemCollection, ids, 'file',
            function (coll) {
                coll.resourceName = 'item/'+ids.item+'/files';
        });
    });

    /* Now test various routes */
    it('logout', girderTest.logout());
    it('test routes without being logged in', function () {
        waitsFor(function () {
            return $('.g-group-link:first').text() === 'Public Group';
        }, 'logout to finish');
        _testRoute('', false, function () {
            return $('a.g-login-link:first').text() === ' Log In';
        });
        _testRoute('useraccount/'+ids.admin+'/info', false, function () {
            return window.location.hash === '#users';
        });
        _testRoute('useraccount/'+ids.admin+'/password', false, function () {
            return window.location.hash === '#users';
        });
        _testRoute('?dialog=login', true, function () {
            return $('label[for=g-login]').text() === 'Login or email';
        });
        _testRoute('?dialog=register', true, function () {
            return $('input#g-password2').length === 1;
        });
        _testRoute('?dialog=resetpassword', true, function () {
            return $('.modal-title').text() === 'Reset password';
        });
        /* Navigate to a non-dialog so we can log in */
        _testRoute('collections', false, function () {
            return $('.g-collection-title:first').text() === 'Test Collection';
        });
    });

    it('login', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    it('test routes while logged in', function () {
        _testRoute('', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
        _testRoute('useraccount/'+ids.admin+'/info', false, function () {
            return $('input#g-email').val() === 'admin@email.com';
        });
        _testRoute('useraccount/'+ids.admin+'/password', false, function () {
            return $('input#g-password-old:visible').length === 1;
        });
        _testRoute('?dialog=login', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
        _testRoute('?dialog=register', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
        _testRoute('?dialog=resetpassword', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
    });

    it('test collection routes', function () {
        _testRoute('collections', false, function () {
            return $('.g-collection-title:first').text() === 'Test Collection';
        });
        _testRoute('collections?dialog=create', true, function () {
            return $('input#g-name').attr('placeholder') ===
                   'Enter collection name';
        });

        var collPath = 'collection/'+ids.collection;
        _testRoute(collPath, false, function () {
            return $('.g-collection-actions-menu').length === 1;
        });
        _testRoute(collPath+'?dialog=edit', true,
                   function () {
            return $('.modal-title').text() === 'Edit collection';
        });
        _testRoute(collPath+'?dialog=access', true,
                   function () {
            return $('.g-dialog-subtitle').text() === 'Test Collection';
        });
        _testRoute(collPath+'?dialog=foldercreate', true,
                   function () {
            return $('.modal-title').text() === 'Create folder';
        });

        var collFolderPath = collPath+'/folder/'+ids.collectionFolder;
        _testRoute(collFolderPath, false, function () {
            return $('.g-collection-actions-menu').length === 1 &&
                   $('.g-folder-access-button').length === 1;
        });
        _testRoute(collFolderPath+'?dialog=edit', true,
                   function () {
            return $('.modal-title').text() === 'Edit collection';
        });
        _testRoute(collFolderPath+'?dialog=access', true,
                   function () {
            return $('.g-dialog-subtitle').text() === 'Test Collection';
        });
        _testRoute(collFolderPath+'?dialog=foldercreate', true,
                   function () {
            return $('.modal-title').text() === 'Create folder';
        });
        _testRoute(collFolderPath+'?dialog=folderedit', true,
                   function () {
            return $('.modal-title').text() === 'Edit folder' &&
                   $('input#g-name').val() === 'Private';
        });
        _testRoute(collFolderPath+'?dialog=folderaccess', true,
                   function () {
            return $('.g-dialog-subtitle').text() === 'Private';
        });
        _testRoute(collFolderPath+'?dialog=itemcreate', true,
                   function () {
            return $('.modal-title').text() === 'Create item';
        });
        _testRoute(collFolderPath+'?dialog=upload', true,
                   function () {
            return $('.modal-title').text() === 'Upload files';
        });
    });

    it('test user routes', function () {
        _testRoute('users', false, function () {
            return $('.g-user-link:first').text() === 'Admin Admin';
        });

        var userPath = 'user/'+ids.admin;
        _testRoute(userPath, false, function () {
            return $('.g-user-actions-button').length === 1;
        });
        _testRoute(userPath+'?dialog=foldercreate', true,
                   function () {
            return $('.modal-title').text() === 'Create folder';
        });

        var userFolderPath = userPath+'/folder/'+ids.userFolder;
        _testRoute(userFolderPath, false, function () {
            return $('.g-user-actions-button').length === 1 &&
                   $('.g-folder-access-button').length === 1;
        });
        _testRoute(userFolderPath+'?dialog=foldercreate', true,
                   function () {
            return $('.modal-title').text() === 'Create folder';
        });
        _testRoute(userFolderPath+'?dialog=folderedit', true,
                   function () {
            return $('.modal-title').text() === 'Edit folder' &&
                   $('input#g-name').val() === 'Private';
        });
        _testRoute(userFolderPath+'?dialog=folderaccess', true,
                   function () {
            return $('.g-dialog-subtitle').text() === 'Private';
        });
        _testRoute(userFolderPath+'?dialog=itemcreate', true,
                   function () {
            return $('.modal-title').text() === 'Create item';
        });
        _testRoute(userFolderPath+'?dialog=upload', true,
                   function () {
            return $('.modal-title').text() === 'Upload files';
        });

        var folderPath = 'folder/'+ids.userFolder;
        _testRoute(folderPath, false, function () {
            return $('.g-user-actions-button').length === 0 &&
                   $('.g-folder-access-button').length === 1;
        });
        _testRoute(folderPath+'?dialog=foldercreate', true,
                   function () {
            return $('.modal-title').text() === 'Create folder';
        });
        _testRoute(folderPath+'?dialog=folderedit', true,
                   function () {
            return $('.modal-title').text() === 'Edit folder' &&
                   $('input#g-name').val() === 'Private';
        });
        _testRoute(folderPath+'?dialog=folderaccess', true,
                   function () {
            return $('.g-dialog-subtitle').text() === 'Private';
        });
        _testRoute(folderPath+'?dialog=itemcreate', true,
                   function () {
            return $('.modal-title').text() === 'Create item';
        });
        _testRoute(folderPath+'?dialog=upload', true,
                   function () {
            return $('.modal-title').text() === 'Upload files';
        });
    });

    it('test group routes', function () {
        _testRoute('groups', false, function () {
            return $('.g-group-link:first').text() === 'Public Group';
        });
        _testRoute('groups?dialog=create', true, function () {
            return $('input#g-name').attr('placeholder') ===
                   'Enter group name';
        });

        var groupPath = 'group/'+ids.group;
        _testRoute(groupPath+'/roles', false, function () {
            return $('.g-member-name:visible').length > 0;
        });
        _testRoute(groupPath+'/pending', false, function () {
            return $('.g-group-requests-container:visible').length === 1 &&
                   $('.g-member-list-empty').length === 2;
        });
        _testRoute(groupPath+'?dialog=edit', true, function () {
            return $('.modal-title').text() === 'Edit group';
        });
    });

    it('test item routes', function () {
        var itemPath = 'item/'+ids.item;
        _testRoute(itemPath, false, function () {
            return $('.g-item-header .g-item-name').text() == 'Link File';
        });
        _testRoute(itemPath+'?dialog=itemedit', true, function () {
            return $('.modal-title').text() === 'Edit item';
        });
        _testRoute(itemPath+'?dialog=fileedit&dialogid='+ids.file, true,
                   function () {
            return $('.modal-title').text() === 'Edit file';
        });
        _testRoute(itemPath+'?dialog=upload&dialogid='+ids.file, true,
                   function () {
            return $('.modal-title').text() === 'Replace file contents';
        });
        _testRoute(itemPath+'?dialog=fileedit&dialogid='+ids.file, true,
                   function () {
            return $('.modal-title').text() === 'Edit file';
        });
    });

    it('test admin routes', function () {
        _testRoute('admin', false, function () {
            return $('.g-server-config').length === 1;
        });
        _testRoute('settings', false, function () {
            return $('input#g-core-cookie-lifetime').length === 1;
        });
        _testRoute('plugins', false, function () {
            return $('.g-body-title').text() === 'Plugins';
        });
        _testRoute('assetstores', false, function () {
            return $('.g-assetstore-container').length === 1;
        });
        _testRoute('assetstores?dialog=assetstoreedit&dialogid='+ids.assetstore,
                    true, function () {
            return $('.modal-title').text() === 'Edit assetstore';
        });
    });
});
