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
            params = fetchParamsFunc();
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
        girderTest.waitForDialog();
    } else {
        girderTest.waitForLoad();
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
    it('collect ids for tests', function () {
        _getFirstId(girder.collections.UserCollection, ids, 'admin');
        _getFirstId(girder.collections.CollectionCollection, ids, 'collection');
        _getFirstId(girder.collections.FolderCollection, ids,
                    'collectionFolder', function(){
            return {parentId: ids.collection, parentType: 'collection'};
        });
    });

    /* Now test various routes */
    it('logout', girderTest.logout());
    it('test routes without being logged in', function () {
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
    });
    
    it('login', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    it('test routes while logged in', function () {
//runs(function () { console.log('__SCREENSHOT__'); }); //DWM::
        _testRoute('', false, function () {
            return $('a.g-my-folders-link:first').text() === ' personal data space';
        });
        _testRoute('useraccount/'+ids.admin+'/info', false, function () {
            return $('input#g-email').val() === 'admin@email.com';
        });
        _testRoute('useraccount/'+ids.admin+'/password', false, function () {
            return $('input#g-password-old').length === 1;
        });
        _testRoute('?dialog=login', false, function () {
            return $('a.g-my-folders-link:first').text() === ' personal data space';
        });
        _testRoute('?dialog=register', false, function () {
            return $('a.g-my-folders-link:first').text() === ' personal data space';
        });
        _testRoute('collections', false, function () {
            return $('.g-collection-title:first').text() === 'Test Collection';
        });
        _testRoute('collections?dialog=create', true, function () {
            return $('input#g-name').attr('placeholder') === 'Enter collection name';
        });
        _testRoute('collection/'+ids.collection, false, function () {
            return $('.g-collection-actions-menu').length === 1;
        });
        _testRoute('collection/'+ids.collection+'?dialog=edit', true, function () {
            return $('.modal-title').text() === 'Edit collection';
        });
        _testRoute('collection/'+ids.collection+'?dialog=access', true, function () {
            return $('.g-dialog-subtitle').text() === 'Test Collection';
        });
        _testRoute('collection/'+ids.collection+'?dialog=foldercreate', true, function () {
            return $('.modal-title').text() === 'Create folder';
        });
        _testRoute('collection/'+ids.collection+'/folder/'+ids.collectionFolder, false, function () {
            return $('.g-collection-actions-menu').length === 1 &&
                   $('.g-folder-access-button').length === 1;
        });
    });
});
