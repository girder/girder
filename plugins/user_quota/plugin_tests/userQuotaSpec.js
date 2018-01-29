girderTest.importPlugin('user_quota');
girderTest.startApp();

/* Go to the collections page.  If a collection is specified, go to that
 * collection's page.
 *
 * @param collection: the name of the collection to go to.
 */
function _goToCollection(collection) {
    runs(function () {
        $('a.g-nav-link[g-target=\'collections\']').click();
    });
    waitsFor(function () {
        return $('.g-collections-search-container:visible').length > 0;
    }, 'navigate to collections page');
    girderTest.waitForLoad();
    if (collection) {
        runs(function () {
            $('a.g-collection-link').has('b:contains(' + collection +
                                         ')').click();
        });
        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');

        girderTest.waitForLoad();
    }
}

/* Go to the users page.  If a user is specified, go to that user's page.
 *
 * @param user: the full name of the user to go to.
 */
function _goToUser(user) {
    girderTest.goToUsersPage()();
    if (user) {
        runs(function () {
            $('a.g-user-link:contains("' + user + '")').click();
        });
        waitsFor(function () {
            return $('.g-user-name').text() === user;
        }, 'user page to appear');
        girderTest.waitForLoad();
    }
}

/* Go to a collection, make it public, and give user1 access to it.
 *
 * @param collection: the name of the collection to go to.
 */
function _makeCollectionPublic(collection) {
    _goToCollection(collection);
    runs(function () {
        $('.g-collection-actions-button').click();
    });
    waitsFor(function () {
        return $('.g-collection-access-control[role="menuitem"]:visible').length === 1;
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
        $('#g-dialog-container .g-search-field').val('user1');
        $('#g-dialog-container input.g-search-field').trigger('input');
    });
    waitsFor(function () {
        return $('.g-search-result').length === 2;
    }, 'user1 to be listed');
    runs(function () {
        $('a.g-search-result-element').click();
    });
    waitsFor(function () {
        return $('.g-user-access-entry').length === 2;
    }, 'user1 to be in the access list');
    runs(function () {
        $('.g-access-col-right select').eq(1).val(2);
    });
    waitsFor(function () {
        return $('.g-save-access-list:visible').is(':enabled') &&
               $('.radio.g-selected').text().match('Public').length > 0;
    }, 'access save button to appear');
    runs(function () {
        $('.g-save-access-list').click();
    });
    girderTest.waitForLoad();
    waitsFor(function () {
        return !$('#g-dialog-container').hasClass('in');
    }, 'access dialog to be hidden');
}

/* Test the quota dialog, expecting that this is an admin and can set the
 * quota.
 * @param: hasChart: if true, we expect a pie chart.  If false, we don't.
 * @param capacity: the capacity in bytes to set.
 */
function _testQuotaDialogAsAdmin(hasChart, capacity) {
    girderTest.waitForDialog('quota dialog to appear');
    waitsFor(function () {
        return $('.g-quota-capacity').length === 1;
    }, 'capacity to appear');
    waitsFor(function () {
        return $('a.btn-default').length === 1;
    }, 'the cancel button to appear');
    waitsFor(function () {
        return $(hasChart ? '.g-has-chart' : '.g-no-chart').length === 1;
    }, 'the chart to be determined (' + hasChart + ' ' + capacity + ')');
    runs(function () {
        expect($('#g-user-quota-size-value').length).toBe(1);
        /* The change() call should automatically set the custom quota radio
         * button. */
        $('#g-user-quota-size-value').val('abc').trigger('input');
        $('.g-save-policies').click();
    });
    waitsFor(function () {
        return $('.g-validation-failed-message').text().indexOf('Invalid quota') >= 0;
    }, 'an error message to appear');
    runs(function () {
        $('#g-user-quota-size-value').val(capacity || '');
    });
    runs(function () {
        $('.g-save-policies').click();
    });
    girderTest.waitForLoad('quota dialog to hide');
}

/* Test the quota dialog, expecting that this is a user and can not set the
 * quota.
 * @param: hasChart: if true, we expect a pie chart.  If false, we don't.
 */
function _testQuotaDialogAsUser(hasChart) {
    girderTest.waitForDialog();
    waitsFor(function () {
        return $('.g-quota-capacity').length === 1;
    }, 'capacity to appear');
    waitsFor(function () {
        return $('a.btn-default').length === 1;
    }, 'the cancel button to appear');
    waitsFor(function () {
        return $(hasChart ? '.g-has-chart' : '.g-no-chart').length === 1;
    }, 'the chart to be determined');
    runs(function () {
        expect($('#g-user-quota-size-value').length).toBe(0);
    });
    runs(function () {
        $('a.btn-default').click();
    });
    girderTest.waitForLoad();
}

describe('test the user quota plugin', function () {
    var collectionDialogRoute, userDialogRoute, userRoute;
    it('create resources', function () {
        girderTest.createUser(
            'admin', 'admin@email.com', 'Quota', 'Admin', 'testpassword')();
        _goToCollection();
        girderTest.createCollection('Collection A', 'ColDescription')();
        _goToCollection();
        girderTest.createCollection('Collection B', 'ColDescription')();
        girderTest.logout('logout from admin')();
        girderTest.createUser(
            'user1', 'user@email.com', 'Quota', 'User', 'testpassword')();
        girderTest.logout('logout from user1')();
        girderTest.createUser(
            'user2', 'user2@email.com', 'Another', 'User', 'testpassword')();
        girderTest.logout('logout from user2')();
        girderTest.createUser(
            'user3', 'user3@email.com', 'Third', 'User', 'testpassword')();
    });
    it('make the collections public', function () {
        girderTest.logout('logout from user3')();
        girderTest.login('admin', 'Quota', 'Admin', 'testpassword')();
        _makeCollectionPublic('Collection A');
        _makeCollectionPublic('Collection B');
    });
    it('check that admin can set the default quotas', function () {
        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]').length > 0;
        }, 'admin console link to load');
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'the admin console to load');
        runs(function () {
            $('.g-plugins-config').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('input.g-plugin-switch[key="user_quota"]').length > 0;
        }, 'the plugins page to load');
        runs(function () {
            expect($('.g-plugin-config-link[g-route="plugins/user_quota/config"]').length > 0);
            $('.g-plugin-config-link[g-route="plugins/user_quota/config"]').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('input.g-sizeValue').length > 0;
        }, 'quota default settings to be shown');
        runs(function () {
            $('input#g-user-quota-user-size-value').val('abc');
            $('#g-user-quota-form input.btn-primary').click();
        });
        waitsFor(function () {
            return $('#g-user-quota-error-message').text().indexOf('Invalid quota') >= 0;
        }, 'error message to appear');
        runs(function () {
            $('input#g-user-quota-user-size-value').val('512000');
            $('#g-user-quota-form input.btn-primary').click();
        });
        waitsFor(function () {
            var resp = girder.rest.restRequest({
                url: 'system/setting',
                method: 'GET',
                data: {key: 'user_quota.default_user_quota'},
                async: false
            });
            return resp.responseText === '512000';
        }, 'default quota settings to change');
        girderTest.waitForLoad();
    });
    it('check that admin can set quota for collections and users', function () {
        _goToCollection('Collection A');
        runs(function () {
            $('.g-collection-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-collection-policies[role="menuitem"]:visible').length === 1;
        }, 'collection actions menu to appear');
        runs(function () {
            $('.g-collection-policies').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            collectionDialogRoute = window.location.hash;
        });
        _testQuotaDialogAsAdmin(false, 2048);
        runs(function () {
            $('.g-collection-policies').click();
        });
        /* We should now have a chart */
        _testQuotaDialogAsAdmin(true, '32 kB');
        _goToUser('Quota User');
        runs(function () {
            userRoute = window.location.hash;
            $('.g-user-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-user-policies[role="menuitem"]:visible').length === 1;
        }, 'user actions menu to appear');
        runs(function () {
            $('.g-user-policies').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            userDialogRoute = window.location.hash;
        });
        _testQuotaDialogAsAdmin(true, 2048);
    });
    it('test routes', function () {
        girderTest.testRoute(collectionDialogRoute, true, function () {
            return $('.g-quota-capacity').length === 1;
        });
        girderTest.testRoute(userRoute, false, function () {
            return $('.g-user-name').text() === 'Quota User';
        });
        girderTest.testRoute(userDialogRoute, true, function () {
            return $('.g-quota-capacity').length === 1;
        });
        runs(function () {
            $('a[data-dismiss="modal"]').click();
        });
        girderTest.waitForLoad();
    });
    it('upload', function () {
        runs(function () {
            $('a.g-folder-list-link').eq(0).click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('li.g-folder-list-entry').length === 0;
        }, 'my folders list to display');
        girderTest.testUpload(2048);
        girderTest.testUpload(2048, 'abort', 'file storage quota');
        runs(function () {
            window.callPhantom({
                action: 'uploadCleanup',
                suffix: girderTest._uploadSuffix
            });
        });
    });
    it('check that user1 can view but not set quota', function () {
        girderTest.logout('logout from admin')();
        girderTest.login('user1', 'Quota', 'User', 'testpassword')();
        _goToCollection('Collection A');
        runs(function () {
            $('.g-collection-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-collection-policies[role="menuitem"]:visible').length === 1;
        }, 'collection actions menu to appear');
        runs(function () {
            $('.g-collection-policies').click();
        });
        _testQuotaDialogAsUser(true);
        _goToUser('Quota User');
        runs(function () {
            $('.g-user-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-user-policies[role="menuitem"]:visible').length === 1;
        }, 'user actions menu to appear');
        runs(function () {
            $('.g-user-policies').click();
        });
        _testQuotaDialogAsUser(true);
    });
    it('check that a different user does not see quota', function () {
        girderTest.logout('logout from user1')();
        girderTest.login('user2', 'Another', 'User', 'testpassword')();
        _goToCollection('Collection A');
        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');
        runs(function () {
            $('.g-collection-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-download-collection[role="menuitem"]:visible').length === 1;
        }, 'collection actions menu to appear');
        runs(function () {
            expect($('.g-collection-policies').length).toBe(0);
        });
        _goToUser('Quota User');
        runs(function () {
            expect($('button:contains("Actions")').length).toBe(0);
        });
    });
    it('check that admin can set the default collection quota', function () {
        girderTest.logout('logout from user2')();
        girderTest.login('admin', 'Quota', 'Admin', 'testpassword')();
        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]').length > 0;
        }, 'admin console link to load');
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'the admin console to load');
        runs(function () {
            $('.g-plugins-config').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('input.g-plugin-switch[key="user_quota"]').length > 0;
        }, 'the plugins page to load');
        runs(function () {
            expect($('.g-plugin-config-link[g-route="plugins/user_quota/config"]').length > 0);
            $('.g-plugin-config-link[g-route="plugins/user_quota/config"]').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('input.g-sizeValue').length > 0;
        }, 'quota default settings to be shown');
        runs(function () {
            $('input#g-user-quota-collection-size-value').val('256000');
            $('#g-user-quota-form input.btn-primary').click();
        });
        waitsFor(function () {
            var resp = girder.rest.restRequest({
                url: 'system/setting',
                method: 'GET',
                data: {key: 'user_quota.default_collection_quota'},
                async: false
            });
            return resp.responseText === '256000';
        }, 'default collection quota settings to change');
        girderTest.waitForLoad();
    });
    it('check that a user that has never had their quota altered sees the default', function () {
        girderTest.logout('logout from admin')();
        girderTest.login('user3', 'Third', 'User', 'testpassword')();
        _goToUser('Third User');
        runs(function () {
            $('.g-user-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-user-policies[role="menuitem"]:visible').length === 1;
        }, 'user actions menu to appear');
        runs(function () {
            $('.g-user-policies').click();
        });
        _testQuotaDialogAsUser(true);
    });
    it('check that a collection that has never had their quota altered sees the default', function () {
        girderTest.logout('logout from user3')();
        girderTest.login('user1', 'Quota', 'User', 'testpassword')();
        _goToCollection('Collection B');
        runs(function () {
            $('.g-collection-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-collection-policies[role="menuitem"]:visible').length === 1;
        }, 'collection actions menu to appear');
        runs(function () {
            $('.g-collection-policies').click();
        });
        _testQuotaDialogAsUser(true);
    });
});
