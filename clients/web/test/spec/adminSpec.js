girderTest.startApp();

describe('Create an admin and non-admin user', function () {
    it('No admin console without logging in', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin console');
    });

    it('register a user (first is admin)',
        girderTest.createUser('admin',
            'admin@email.com',
            'Admin',
            'Admin',
            'adminpassword!'));

    it('Admin console should show when admin is logged in', function () {
        expect($('.g-global-nav-li span').text()).toContain('Admin console');
    });

    it('logout from admin account', girderTest.logout());

    it('No admin console directly after admin logs out', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin console');
    });

    waitsFor(function () {
        return $('.g-frontpage-title:visible').length > 0;
    }, 'front page to display');

    it('register a (normal user)',
        girderTest.createUser('johndoe',
            'john.doe@email.com',
            'John',
            'Doe',
            'password!'));

    it('No admin console when logging in as a normal user', function () {
        expect($('.g-global-nav-li span').text()).not.toContain('Admin console');
    });

    it('go to groups page', girderTest.goToGroupsPage());

    it('Create a public group',
        girderTest.createGroup('pubGroup', 'public group', true));
});

describe('Test the settings page', function () {
    it('Logout', girderTest.logout());

    it('Test that anonymous loading settings page prompts login', function () {
        girderTest.anonymousLoadPage(false, 'settings', true);
    });

    it('Login as admin', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    it('Go to settings page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });

        waitsFor(function () {
            return $('.g-server-config').length > 0;
        }, 'admin page to load');
        girderTest.waitForLoad();

        runs(function () {
            $('.g-server-config').click();
        });

        waitsFor(function () {
            return $('input#g-core-cookie-lifetime').length > 0;
        }, 'settings page to load');
        girderTest.waitForLoad();
    });

    it('Settings should display their expected values', function () {
        expect($('#g-core-cookie-lifetime').val()).toBe('');
        expect($('#g-core-smtp-host').val()).toMatch(/^localhost:31/);
        expect($('#g-core-email-from-address').val()).toBe('');
        expect($('#g-core-brand-name').val()).toBe('');
        expect($('#g-core-contact-email-address').val()).toBe('');
        expect($('#g-core-registration-policy').val()).toBe('open');
        expect($('#g-core-upload-minimum-chunk-size').val()).toBe('');
        expect(JSON.parse($('#g-core-collection-create-policy').val())).toEqual({
            open: false,
            users: [],
            groups: []
        });
    });
    it('Change settings', function () {
        runs(function () {
            $('#g-core-cookie-lifetime').val('not a number');
            $('.g-submit-settings').click();
        });
        waitsFor(function () {
            return $('#g-settings-error-message').text() === 'Cookie lifetime must be an integer > 0.';
        }, 'error message to be shown');
        runs(function () {
            $('#g-core-cookie-lifetime').val('180');
            $('.g-submit-settings').click();
        });
        waitsFor(function () {
            return $('#g-settings-error-message').text() === '';
        }, 'error message to be cleared');
        runs(function () {
            $('#g-core-brand-name').val('fooBar');
            $('.g-submit-settings').click();
        });
        waitsFor(function () {
            return $('#g-core-brand-name').val() === 'fooBar';
        }, 'brand name to change');
        runs(function () {
            $('#g-core-contact-email-address').val('foo@foo.com');
            $('.g-submit-settings').click();
        });
        waitsFor(function () {
            return $('#g-core-contact-email-address').val() === 'foo@foo.com';
        }, 'contact email address to change');
    });
    it('Use search to update collection create policy', function () {
        runs(function () {
            $('.g-collection-create-policy-container .g-plugin-switch').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .access-widget-container .g-grant-access-container').length > 0;
        }, 'access widget to load');

        runs(function () {
            $('.g-collection-create-policy-container .g-search-field').val('admin')
                .trigger('input');
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .g-search-result').length > 0;
        }, 'search result to appear for a user');

        runs(function () {
            $('.g-collection-create-policy-container .g-search-result-element').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .access-widget-container #g-ac-list-users').children().length === 1;
        }, 'access list to populate with one user');

        runs(function () {
            $('.g-collection-create-policy-container .g-search-field').val('pubGroup').trigger('input');
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .g-search-result .icon-users').length > 0;
        }, 'search result to appear for a group');

        runs(function () {
            $('.g-collection-create-policy-container .g-search-result-element').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .access-widget-container #g-ac-list-groups').children().length === 1;
        }, 'access list to populate with one group');

        runs(function () {
            $('.g-submit-settings').click();
        });

        runs(function () {
            $('.g-collection-create-policy-container .access-widget-container #g-ac-list-users .g-user-access-entry .icon-cancel').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .access-widget-container #g-ac-list-users').children().length === 0;
        }, 'policy value to be cleared');

        runs(function () {
            $('.g-collection-create-policy-container .g-plugin-switch').click();
        });

        waitsFor(function () {
            return $('.g-collection-create-policy-container .access-widget-container .g-grant-access-container').length === 0;
        }, 'access widget unload');
    });

    it('logout and check for redirect to front page from settings page', function () {
        girderTest.logout()();

        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });
});

describe('Test the assetstore page', function () {
    var name, service;

    var _getAssetstoreContainer = function (name) {
        var containers = $('.g-assetstore-container');
        for (var i = 0; i < containers.length; i++) {
            if ($('span.g-assetstore-name', containers.eq(i)).text().trim() === name) {
                return containers.eq(i);
            }
        }
        return null;
    };

    var _testAssetstore = function (assetstore, tab, params, callback, waitCondition, waitMessage, shouldFail) {
        var storeName = 'Test ' + assetstore + ' Assetstore';

        it('Create, switch to, and delete a ' + assetstore + ' assetstore', function () {
            /* create the assetstore */
            runs(function () {
                $('[data-target="#' + tab + '"]').click();
            });
            waitsFor(function () {
                return $('#' + tab + ' .g-new-assetstore-submit:visible').length > 0;
            }, assetstore + ' tab to open');
            runs(function () {
                $('#' + tab + ' .g-new-assetstore-submit').click();
            });
            waitsFor(function () {
                return $('#' + tab + ' .g-validation-failed-message:visible').text().length > 0;
            }, 'failure message to appear');
            runs(function () {
                name = storeName;
                for (var key in params) {
                    var value = params[key];
                    if (value === 'name') {
                        value = name;
                    }
                    if (value === 'service') {
                        value = service;
                    }
                    if ($('input#' + key).is(':checkbox')) {
                        $('input#' + key).attr('checked', value);
                    } else {
                        $('input#' + key).val(value);
                    }
                }
            });
            waitsFor(function () {
                return $('#' + tab + ' .g-new-assetstore-submit[disabled]').length === 0;
            }, 'create assetstore button to be re-enabled');
            runs(function () {
                $('#' + tab + ' .g-new-assetstore-submit').click();
            });
            waitsFor(waitCondition || function () {
                return _getAssetstoreContainer(name) !== null;
            }, waitMessage || 'assetstore to be listed', 20000);

            if (shouldFail) {
                return;
            }

            /* make this the current assetstore */
            runs(function () {
                $('.g-set-current', _getAssetstoreContainer(name)).click();
            });
            waitsFor(function () {
                var container = _getAssetstoreContainer(name);
                return $('.g-set-current', container).length === 0;
            }, 'assetstore to be current');
            waitsFor(function () {
                return $('#g-dialog-container:visible').length === 0;
            }, 'all elements to be visible');

            /* edit the assetstore's name */
            runs(function () {
                $('.g-edit-assetstore', _getAssetstoreContainer(name)).click();
            });
            girderTest.waitForDialog();
            waitsFor(function () {
                return $('.g-save-assetstore.btn:visible').length > 0 &&
                       $('#g-edit-name').val() === name;
            }, 'edit confirmation to appear and name field to be present');
            runs(function () {
                name += ' Edit';
                $('input#g-edit-name').val('');
                $('.g-save-assetstore.btn').click();
            });
            waitsFor(function () {
                return $('#g-dialog-container .g-validation-failed-message').text() === 'Name must not be empty.';
            }, 'name empty error to appear');

            runs(function () {
                name += ' Edit';
                $('input#g-edit-name').val(name);
                $('.g-save-assetstore.btn').click();
            });
            waitsFor(function () {
                return _getAssetstoreContainer(name) !== null;
            }, 'assetstore to be changed');
            girderTest.waitForLoad();

            /* edit and dismiss */
            runs(function () {
                $('.g-edit-assetstore', _getAssetstoreContainer(name)).click();
            });
            girderTest.waitForDialog();
            waitsFor(function () {
                return $('.g-save-assetstore.btn:visible').length > 0 &&
                       $('#g-edit-name').val() === name;
            }, 'edit confirmation to appear and name field to be present');
            runs(function () {
                $('a[data-dismiss="modal"]').click();
            });
            girderTest.waitForLoad();

            /* navigate away and back */
            runs(function () {
                $('a.g-nav-link[g-target="admin"]').click();
            });
            waitsFor(function () {
                return $('.g-assetstore-config').length > 0;
            }, 'admin page to load');
            runs(function () {
                $('.g-assetstore-config').click();
            });
            waitsFor(function () {
                return $('.g-assetstore-container').length > 0;
            }, 'assetstore page to load');

            if (callback) {
                runs(function () {
                    callback({ // eslint-disable-line standard/no-callback-literal
                        name: name
                    });
                });
            }

            /* delete the assetstore */
            runs(function () {
                $('.g-delete-assetstore', _getAssetstoreContainer(name)).click();
            });
            girderTest.waitForDialog();
            waitsFor(function () {
                return $('#g-confirm-button:visible').length > 0;
            }, 'delete confirmation to appear');
            runs(function () {
                $('#g-confirm-button').click();
            });
            waitsFor(function () {
                return _getAssetstoreContainer(name) === null;
            }, 'assetstore to be deleted');
            runs(function () {
                /* The original assetstore should be back to being the current
                 * assetstore */
                var container = _getAssetstoreContainer('Test');
                expect($('.g-set-current', container).length).toBe(0);
            });
            girderTest.waitForLoad();
        });
    };

    var _testFilesystemImport = function (params) {
        var privateFolder = null;

        runs(function () {
            var container = _getAssetstoreContainer(params.name);
            var el = $('a.g-import-button', container);
            window.location = el[0].href;
        });

        waitsFor(function () {
            return $('input#g-filesystem-import-path').length > 0;
        }, 'import page to load');

        runs(function () {
            var coll = new girder.collections.FolderCollection();
            coll.on('g:changed', function () {
                privateFolder = coll.models[0];
            }).fetch({
                parentType: 'user',
                parentId: girder.auth.getCurrentUser().id
            });
        });

        waitsFor(function () {
            return privateFolder !== null;
        }, 'admin user folders to be fetched');

        runs(function () {
            $('#g-filesystem-import-dest-id').val(privateFolder.id);
            $('#g-filesystem-import-dest-type').val('folder');
            $('#g-filesystem-import-path').val('/invalid/path');

            $('.g-submit-assetstore-import').click();
        });

        waitsFor(function () {
            return $('.g-validation-failed-message').text() ===
                'Not found: /invalid/path.';
        }, 'not found message to appear');

        runs(function () {
            $('#g-filesystem-import-path').val('./tests/cases/py_client');

            $('.g-submit-assetstore-import').click();
        });

        waitsFor(function () {
            return $('.g-folder-list-entry').text().indexOf('testdata') !== -1;
        }, 'user folders to show');

        runs(function () {
            _.each($('.g-folder-list-link'), function (link) {
                if ($(link).text() === 'testdata') {
                    $(link).click();
                }
            });
        });

        waitsFor(function () {
            return $('.g-item-list-link').text().indexOf('hello.txt') !== -1;
        }, 'item to appear in the hierarchy widget');

        runs(function () {
            $('.g-item-list-link').click();
        });

        waitsFor(function () {
            return $('.g-file-list-link').length === 1;
        }, 'item page to render');

        // Delete the containing folder so we can delete the assetstore
        runs(function () {
            privateFolder.on('g:deleted', function () {
                privateFolder = null;
            }).destroy();
        });

        waitsFor(function () {
            return privateFolder === null;
        }, 'private folder to be deleted');

        runs(function () {
            window.location = '#assetstores';
        });

        waitsFor(function () {
            return $('.g-assetstore-container').length > 0;
        }, 'assetstore page to load');
    };

    var _testS3Import = function (params) {
        var privateFolder = null;

        runs(function () {
            var container = _getAssetstoreContainer(params.name);
            var el = $('a.g-import-button', container);
            window.location = el[0].href;
        });

        waitsFor(function () {
            return $('input#g-s3-import-path').length > 0;
        }, 'import page to load');

        runs(function () {
            var coll = new girder.collections.FolderCollection();
            coll.on('g:changed', function () {
                privateFolder = coll.models[0];
            }).fetch({
                parentType: 'user',
                parentId: girder.auth.getCurrentUser().id
            });
        });

        waitsFor(function () {
            return privateFolder !== null;
        }, 'admin user folders to be fetched');

        runs(function () {
            $('#g-s3-import-dest-id').val(privateFolder.id);
            $('#g-s3-import-dest-type').val('folder');

            $('.g-submit-s3-import').click();
        });

        waitsFor(function () {
            return $('.g-empty-parent-message').length > 0;
        }, 'user folders to show');

        runs(function () {
            window.location = '#assetstores';
        });

        waitsFor(function () {
            return $('.g-assetstore-container').length > 0;
        }, 'assetstore page to load');
    };

    it('Test that anonymous loading assetstore page prompts login', function () {
        girderTest.anonymousLoadPage(false, 'assetstores', true);
    });

    it('Go to assetstore page', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();

        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });

        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });

        waitsFor(function () {
            return $('.g-assetstore-config').length > 0;
        }, 'admin page to load');

        runs(function () {
            $('.g-assetstore-config').click();
        });

        waitsFor(function () {
            return $('.g-assetstore-container').length > 0;
        }, 'assetstore page to load');

        runs(function () {
            /* Store the service used by the test assetstore, as it may be at
             * an arbitrary port. */
            service = $('.g-service-key').text().replace(/^\s+|\s+$/g, '');
            expect(service).toMatch(/^http:\/\/127\.0\.0\.1:/);
        });
    });

    _testAssetstore('filesystem', 'g-create-fs-tab', {
        'g-new-fs-name': 'name',
        'g-new-fs-root': '/tmp/assetstore'
    }, _testFilesystemImport);

    _testAssetstore('gridfs', 'g-create-gridfs-tab', {
        'g-new-gridfs-name': 'name',
        'g-new-gridfs-db': 'girder_webclient_gridfs'
    });

    /* The specified assetstore should NOT exist, and the specified mongohost
     * should NOT be present (nothing should respond on those ports). */
    _testAssetstore('gridfs-rs', 'g-create-gridfs-tab', {
        'g-new-gridfs-name': 'name',
        'g-new-gridfs-db': 'girder_webclient_gridfsrs',
        'g-new-gridfs-mongohost': 'mongodb://127.0.0.2:27080,127.0.0.2:27081,' +
                                  '127.0.0.2:27082/?serverSelectionTimeoutMS=250',
        'g-new-gridfs-replicaset': 'replicaset',
        'g-new-gridfs-shard-auto': false
    }, null, function () {
        return $('.g-validation-failed-message:contains(' +
                 '"Could not connect to the database: ")').length === 1;
    }, 'validation failure to display', true);

    _testAssetstore('s3', 'g-create-s3-tab', {
        'g-new-s3-name': 'name',
        'g-new-s3-bucket': 'bucketname',
        'g-new-s3-prefix': 'prefix',
        'g-new-s3-access-key-id': 'test',
        'g-new-s3-secret': 'test',
        'g-new-s3-service': 'service'
    }, _testS3Import);

    /* Logout to make sure we don't see the assetstores any more */
    it('logout from admin account', girderTest.logout('logout to no longer view asset stores'));
    it('logout and check for redirect to front page from assetstore page', function () {
        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });
});

// TODO: Add plugins to satisfy these test cases to the web_client test case.
xdescribe('Test the plugins page', function () {
    beforeEach(function () {
        spyOn(girder.server.restartServer, '_callSystemRestart').andCallFake(function () {
            var restartResolution = $.Deferred();
            window.setTimeout(function () {
                girder.server.restartServer._lastStartDate = 0;
                restartResolution.resolve();
            }, 100);
            return restartResolution.promise();
        });
        spyOn(girder.server.restartServer, '_reloadWindow');
    });

    it('Test that anonymous loading plugins page prompts login', function () {
        girderTest.anonymousLoadPage(false, 'plugins', true);
    });

    it('Login as admin', girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    it('Go to plugins page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'admin page to load');
        girderTest.waitForLoad();

        runs(function () {
            $('.g-plugins-config').click();
        });

        waitsFor(function () {
            return $('.g-plugin-list-item').length > 0;
        }, 'plugins page to load');
        girderTest.waitForLoad();
    });
    it('Check that an error indicator is displayed for an enabled plugin that failed to load', function () {
        var target = $('.g-plugin-list-item:contains(bad_server)');
        expect(target.length).toBe(1);
        expect(target.find('input[type=checkbox]:checked').length).toBe(1);
        expect(target.hasClass('g-plugin-list-item-failed')).toBe(true);
        expect(target.find('.g-plugin-list-item-failed-notice').length).toBe(1);

        var content = target.find('.g-plugin-list-item-failed-notice').data('content');
        expect(content).toContain('Traceback');
        expect(content).toContain('Exception: Bad server');
    });
    it('Enable a plugin with non-existent dependencies', function () {
        runs(function () {
            var target = $('.g-plugin-list-item:contains(has_nonexistent_deps)');

            expect(target.find('.bootstrap-switch-disabled').length > 0).toBe(true);
            expect(target.find('.g-plugin-warning').length > 0).toBe(true);

            target.find('.g-plugin-switch').click();

            expect($('.g-plugin-restart-text').css('visibility')).toBe('hidden');
        });
    });
    it('Enable a plugin', function () {
        runs(function () {
            expect($('.g-plugin-list-item .bootstrap-switch').length > 0).toBe(true);
            expect($('.g-plugin-restart-text').css('visibility')).toBe('hidden');
            expect($('.g-plugin-list-item input[type=checkbox]:checked').length).toBe(1);
            $('.g-plugin-list-item:contains(test_plugin) .g-plugin-switch').click();
        });
        waitsFor(function () {
            return $('.g-plugin-restart-text').css('visibility') === 'visible' &&
                $('.g-restart').hasClass('btn-danger');
        }, 'restart change color and restart messsage to be shown');
        runs(function () {
            expect($('.g-plugin-list-item input[type=checkbox]:checked').length).toBe(2);
            $('.g-restart').click();
        });
        waitsFor(function () {
            return $('#g-confirm-button:visible').length > 0;
        }, 'restart confirmation to appear');
        runs(function () {
            $('#g-confirm-button').click();
        });
        waitsFor(function () {
            return girder.server.restartServer._callSystemRestart.wasCalled &&
                   girder.server.restartServer._reloadWindow.wasCalled;
        }, 'restart to be called');
    });
    it('Go away and back to plugins page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'admin page to load');
        girderTest.waitForLoad();

        runs(function () {
            $('.g-plugins-config').click();
        });

        waitsFor(function () {
            return $('.g-plugin-list-item').length > 0;
        }, 'plugins page to load');
        girderTest.waitForLoad();
    });
    it('Disable a plugin', function () {
        runs(function () {
            $('.g-plugin-list-item:contains(test_plugin) .g-plugin-switch').click();
        });
        runs(function () {
            expect($('.g-plugin-list-item input[type=checkbox]:checked').length).toBe(1);
        });
        waitsFor(function () {
            var resp = girder.rest.restRequest({
                url: 'system/plugins',
                method: 'GET',
                async: false
            });
            return (resp && resp.responseJSON && resp.responseJSON.enabled &&
                resp.responseJSON.enabled.length === 1);
        });
    });
    /* Logout to make sure we don't see the plugins any more */
    it('log out and check for redirect to front page from plugins page', function () {
        girderTest.logout('logout to no longer view plugins page')();

        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });
});
