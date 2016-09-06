/**
 * Start the girder backbone app.
 */
girderTest.startApp();

function _getFirstId(collection, ids, key, fetchParamsFunc) {
    var coll;
    runs(function () {
        coll = new collection();
        var params;
        if (fetchParamsFunc) {
            params = fetchParamsFunc(coll);
        }
        coll.fetch(params);
    });
    waitsFor(function () {
        return coll.length > 0;
    }, 'collection to load');
    runs(function () {
        ids[key] = coll.first().get('_id');
    });
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
                                    'Collection Description', 'Private'));

    it('make the collection public', function () {
        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');
        runs(function () {
            $('.g-collection-actions-button').click();
        });
        waitsFor(function () {
            return $(".g-collection-access-control[role='menuitem']:visible").length === 1;
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
                    'collectionFolder',
            function () {
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
            girder.rest.restRequest({type:'POST', path:'file', data: {
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
                coll.resourceName = 'item/' + ids.item + '/files';
            });
    });

    /* Now test various routes */
    it('logout', girderTest.logout());
    it('test routes without being logged in', function () {
        girderTest.testRoute('', false, function () {
            return $('a.g-login-link:first').text() === ' Log In';
        });
        girderTest.testRoute('useraccount/' + ids.admin + '/info', false,
            function () {
                return window.location.hash === '#users';
            });
        girderTest.testRoute('useraccount/' + ids.admin + '/password', false,
            function () {
                return window.location.hash === '#users';
            });
        girderTest.testRoute('?dialog=login', true, function () {
            return $('label[for=g-login]').text() === 'Login or email';
        });
        girderTest.testRoute('?dialog=register', true, function () {
            return $('input#g-password2').length === 1;
        });
        girderTest.testRoute('?dialog=resetpassword', true, function () {
            return $('.modal-title').text() === 'Forgotten password';
        });
        /* Navigate to a non-dialog so we can log in */
        girderTest.testRoute('collections', false, function () {
            return $('.g-collection-title:first').text() === 'Test Collection';
        });
    });

    it('login', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    it('test routes while logged in', function () {
        girderTest.testRoute('', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
        girderTest.testRoute('useraccount/' + ids.admin + '/info', false,
            function () {
                return $('input#g-email').val() === 'admin@email.com';
            });
        girderTest.testRoute('useraccount/' + ids.admin + '/password', false,
            function () {
                return $('input#g-password-old:visible').length === 1;
            });
        girderTest.testRoute('?dialog=login', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
        girderTest.testRoute('?dialog=register', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
        girderTest.testRoute('?dialog=resetpassword', false, function () {
            return $('a.g-my-folders-link:first').text() ===
                   ' personal data space';
        });
    });

    it('test collection routes', function () {
        girderTest.testRoute('collections', false, function () {
            return $('.g-collection-title:first').text() === 'Test Collection';
        });
        girderTest.testRoute('collections?dialog=create', true, function () {
            return $('input#g-name').attr('placeholder') ===
                   'Enter collection name';
        });

        var collPath = 'collection/' + ids.collection;
        girderTest.testRoute(collPath, false, function () {
            return $('.g-collection-actions-menu').length === 1;
        });
        girderTest.testRoute(collPath + '?dialog=edit', true,
            function () {
                return $('.modal-title').text() === 'Edit collection';
            });
        girderTest.testRoute(collPath + '?dialog=access', true,
            function () {
                return $('.g-dialog-subtitle').text() === 'Test Collection';
            });
        girderTest.testRoute(collPath + '?dialog=foldercreate', true,
            function () {
                return $('.modal-title').text() === 'Create folder';
            });

        var collFolderPath = collPath + '/folder/' + ids.userFolder;
        girderTest.testRoute(collFolderPath, false, function () {
            return $('.g-collection-actions-menu').length === 1 &&
                   $('.g-folder-access-button').length === 1;
        });
        girderTest.testRoute(collFolderPath + '?dialog=edit', true,
            function () {
                return $('.modal-title').text() === 'Edit collection';
            });
        girderTest.testRoute(collFolderPath + '?dialog=access', true,
            function () {
                return $('.g-dialog-subtitle').text() === 'Test Collection';
            });
        girderTest.testRoute(collFolderPath + '?dialog=foldercreate', true,
            function () {
                return $('.modal-title').text() === 'Create folder';
            });
        girderTest.testRoute(collFolderPath + '?dialog=folderedit', true,
            function () {
                return $('.modal-title').text() === 'Edit folder' &&
                       $('input#g-name').val() === 'Private';
            });
        girderTest.testRoute(collFolderPath + '?dialog=folderaccess', true,
            function () {
                return $('.g-dialog-subtitle').text() === 'Private';
            });
        girderTest.testRoute(collFolderPath + '?dialog=itemcreate', true,
            function () {
                return $('.modal-title').text() === 'Create item';
            });
        girderTest.testRoute(collFolderPath + '?dialog=upload', true,
            function () {
                return $('.modal-title').text() === 'Upload files';
            });
    });

    it('test user routes', function () {
        girderTest.testRoute('users', false, function () {
            return $('.g-user-link:first').text() === 'Admin Admin';
        });

        var userPath = 'user/' + ids.admin;
        girderTest.testRoute(userPath, false, function () {
            return $('.g-user-actions-button').length === 1;
        });
        girderTest.testRoute(userPath + '?dialog=foldercreate', true,
            function () {
                return $('.modal-title').text() === 'Create folder';
            });

        var userFolderPath = userPath + '/folder/' + ids.userFolder;
        girderTest.testRoute(userFolderPath, false, function () {
            return $('.g-user-actions-button').length === 1 &&
                   $('.g-folder-access-button').length === 1;
        });
        girderTest.testRoute(userFolderPath + '?dialog=foldercreate', true,
            function () {
                return $('.modal-title').text() === 'Create folder';
            });
        girderTest.testRoute(userFolderPath + '?dialog=folderedit', true,
            function () {
                return $('.modal-title').text() === 'Edit folder' &&
                       $('input#g-name').val() === 'Private';
            });
        girderTest.testRoute(userFolderPath + '?dialog=folderaccess', true,
            function () {
                return $('.g-dialog-subtitle').text() === 'Private';
            });
        girderTest.testRoute(userFolderPath + '?dialog=itemcreate', true,
            function () {
                return $('.modal-title').text() === 'Create item';
            });
        girderTest.testRoute(userFolderPath + '?dialog=upload', true,
            function () {
                return $('.modal-title').text() === 'Upload files';
            });

        var folderPath = 'folder/' + ids.userFolder;
        girderTest.testRoute(folderPath, false, function () {
            return $('.g-user-actions-button').length === 0 &&
                   $('.g-folder-access-button').length === 1;
        });
        girderTest.testRoute(folderPath + '?dialog=foldercreate', true,
            function () {
                return $('.modal-title').text() === 'Create folder';
            });
        girderTest.testRoute(folderPath + '?dialog=folderedit', true,
            function () {
                return $('.modal-title').text() === 'Edit folder' &&
                       $('input#g-name').val() === 'Private';
            });
        girderTest.testRoute(folderPath + '?dialog=folderaccess', true,
            function () {
                return $('.g-dialog-subtitle').text() === 'Private';
            });
        girderTest.testRoute(folderPath + '?dialog=itemcreate', true,
            function () {
                return $('.modal-title').text() === 'Create item';
            });
        girderTest.testRoute(folderPath + '?dialog=upload', true,
            function () {
                return $('.modal-title').text() === 'Upload files';
            });
    });

    it('test group routes', function () {
        girderTest.testRoute('groups', false, function () {
            return $('.g-group-link:first').text() === 'Public Group';
        });
        girderTest.testRoute('groups?dialog=create', true, function () {
            return $('input#g-name').attr('placeholder') ===
                   'Enter group name';
        });

        var groupPath = 'group/' + ids.group;
        girderTest.testRoute(groupPath + '/roles', false, function () {
            return $('.g-member-name:visible').length === 1 &&
                   $('#g-group-tab-roles .g-member-list-empty:visible')
                   .length === 2 &&
                   $('.g-member-list-empty:hidden').length === 2;
        });
        girderTest.testRoute(groupPath + '/pending', false, function () {
            return $('.g-group-requests-container:visible').length === 1 &&
                   $('#g-group-tab-pending .g-member-list-empty:visible')
                   .length === 2 &&
                   $('.g-member-list-empty:hidden').length === 2;
        });
        girderTest.testRoute(groupPath + '?dialog=edit', true, function () {
            return $('.modal-title').text() === 'Edit group';
        });
    });

    it('test item routes', function () {
        var itemPath = 'item/' + ids.item;
        girderTest.testRoute(itemPath, false, function () {
            return $('.g-item-header .g-item-name').text() === 'Link File';
        });
        girderTest.testRoute(itemPath + '?dialog=itemedit', true,
            function () {
                return $('.modal-title').text() === 'Edit item';
            });
        girderTest.testRoute(itemPath + '?dialog=fileedit&dialogid=' +
            ids.file, true, function () {
                return $('.modal-title').text() === 'Edit file';
            });
        girderTest.testRoute(itemPath + '?dialog=upload&dialogid=' +
            ids.file, true, function () {
                return $('.modal-title').text() === 'Replace file contents';
            });
        girderTest.testRoute(itemPath + '?dialog=fileedit&dialogid=' +
            ids.file, true, function () {
                return $('.modal-title').text() === 'Edit file';
            });
    });

    it('test admin routes', function () {
        girderTest.testRoute('admin', false, function () {
            return $('.g-server-config').length === 1;
        });
        girderTest.testRoute('settings', false, function () {
            return $('input#g-core-cookie-lifetime').length === 1;
        });
        girderTest.testRoute('plugins', false, function () {
            return $('.g-body-title').text() === 'Plugins';
        });
        girderTest.testRoute('assetstores', false, function () {
            return $('.g-assetstore-container').length === 1;
        });
        girderTest.testRoute('assetstores?dialog=assetstoreedit&dialogid=' +
            ids.assetstore, true, function () {
                return $('.modal-title').text() === 'Edit assetstore';
            });
    });
});

describe('Test internal javascript functions', function () {
    it('check parseQueryString', function () {
        runs(function () {
            var testVals = [
                {plain: 'strings'},
                {altchar: 'a~`!@#$%^&*()_+{}|[]\\:";\'<>?,./'}
            ];
            for (var i = 0; i < testVals.length; i += 1) {
                var encode = $.param(testVals[i]);
                expect($.param(girder.misc.parseQueryString(encode))).toBe(encode);
            }
        });
    });
});

describe('Test disabling the router at runtime', function () {
    var router = Backbone.Router.prototype;

    beforeEach(function () {
        spyOn(router, 'navigate');
    });

    it('router should be enabled by default', function () {
        girder.router.navigate('collections', {trigger: true});

        expect(router.navigate).toHaveBeenCalled();
    });

    it('disabling router should make navigate() a no-op', function () {
        girder.router.enabled(false);

        girder.router.navigate('users', {trigger: true});

        expect(router.navigate).not.toHaveBeenCalled();
    });
});
