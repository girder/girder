girderTest.startApp();

/* Search for a name on the members search panel, and invite or add the first
 * found user as a member, moderator, or admin.
 *
 * @param name: name to search for.
 * @param level: 'member', 'moderator', or 'admin'.
 * @param action: 'invite' or 'add.
 * @param check: if true or false, assert if the action exists, then cancel the
 *               dialog.
 */
function _invite(name, level, action, check) {
    // Search for the named user in user search box
    waitsFor(function () {
        return $('.g-group-invite-container input.g-search-field').length > 0;
    }, 'search field widget to render');

    runs(function () {
        $('.g-group-invite-container input.g-search-field').val(name).trigger('input');
    });
    girderTest.waitForLoad();
    waitsFor(function () {
        return $('.g-group-invite-container .g-search-results').hasClass('open');
    }, 'search to return (' + name + ')');
    runs(function () {
        var results = $('.g-group-invite-container li.g-search-result');
        expect(results.length).toBe(2); // 1 + '...' element

        expect(results.find('a[data-resource-type="user"]').length).toBe(1);

        results.find('a[data-resource-type="user"]').click();
    });
    girderTest.waitForDialog();
    waitsFor(function () {
        return $('.g-invite-as-member.btn').length === 1;
    }, 'invitation dialog to appear with invite button');
    runs(function () {
        var sel = 'member';
        switch (level) {
            case 'moderator': sel = 'moderator'; break;
            case 'admin': sel = 'administrator'; break;
        }
        if (sel !== 'member') {
            $('.panel-title:contains("Invite as ' + sel + '") a').click();
        }
    });
    runs(function () {
        if (check === true) {
            expect($('.g-' + action + '-as-' + level).length).toBe(1);
            $('.modal-footer a').click();
        } else if (check === false) {
            expect($('.g-' + action + '-as-' + level).length).toBe(0);
            expect($('.g-invite-as-' + level).length).toBe(1);
            $('.modal-footer a').click();
        } else {
            $('.g-' + action + '-as-' + level).click();
        }
    });
    girderTest.waitForLoad();
}

/* Test if a combination of user and add-to-group policy has the expected
 * ability to directly add members.
 *
 * @param policy: a dictionary of user, setting, and mayAdd.  user is the name
 *                of the user to test, setting is the value for the policy, and
 *                mayAdd is either null (no invitation dialog), or a boolean
 *                (true if direct adds are allowed).
 * @param curUser: the current logged in user.
 * @param curSetting: the current policy setting.
 */
function _testDirectAdd(policy, curUser, curSetting) {
    if (curSetting !== policy.setting) {
        if (curUser !== 'admin') {
            girderTest.logout()();
            girderTest.login('admin', 'Admin', 'Admin',
                'adminpassword!')();
            curUser = 'admin';
        }
        runs(function () {
            girder.rest.restRequest({
                url: 'system/setting',
                method: 'PUT',
                data: {
                    key: 'core.add_to_group_policy',
                    value: policy.setting
                },
                async: false
            });
        });
        /* Navigate away and back to make the group reload unless we are going
         * to change users */
        if (curUser === policy.user) {
            girderTest.goToGroupsPage()();
            waitsFor(function () {
                return $('.g-group-list-entry').length === 2 &&
                       $('.g-group-list-entry:contains("pubGroup") .g-group-link').length === 1;
            }, 'the two groups to show up');
            runs(function () {
                $('.g-group-list-entry:contains("pubGroup") .g-group-link').click();
            });
            waitsFor(function () {
                return $('.g-group-name').text() === 'pubGroup' &&
                       $('.g-group-members>li').length === 1 &&
                       $('.g-group-mods>li').length === 1 &&
                       $('.g-group-admins>li').length === 2;
            }, 'the group page to load');
        }
    }
    if (curUser !== policy.user) {
        girderTest.logout()();
        if (policy.user === 'admin') {
            girderTest.login('admin', 'Admin', 'Admin',
                'adminpassword!')();
        } else {
            girderTest.login(
                'user' + policy.user, 'User' + policy.user, 'User',
                'password!')();
        }
        curUser = policy.user;
        // go back to the groups page since we've logged out
        girderTest.goToGroupsPage()();
        waitsFor(function () {
            return $('.g-group-list-entry').length >= 1 &&
                   $('.g-group-list-entry:contains("pubGroup") .g-group-link').length === 1;
        }, 'the public groups to show up');
        runs(function () {
            $('.g-group-list-entry:contains("pubGroup") .g-group-link').click();
        });
        waitsFor(function () {
            return $('.g-group-name').text() === 'pubGroup' &&
                   $('.g-group-members>li').length === 1 &&
                   $('.g-group-mods>li').length === 1 &&
                   $('.g-group-admins>li').length === 2;
        }, 'the group page to load');
    }
    /* If the invite search field exists or we think it should,
     * test that the add button exists as we expect */
    if (policy.mayAdd === null) {
        runs(function () {
            expect($('.g-group-invite-container input.g-search-field').length
            ).toBe(0);
        });
    } else {
        _invite('admin', 'member', 'add', policy.mayAdd);
    }
}

describe('Test group actions', function () {
    it('register a user (first is admin)',
        girderTest.createUser('admin',
            'admin@email.com',
            'Admin',
            'Admin',
            'adminpassword!'));

    it('go to groups page', girderTest.goToGroupsPage());

    it('check that groups page is blank', function () {
        runs(function () {
            expect($('.g-group-list-entry').length).toBe(0);
        });
    });

    it('Create a private group',
        girderTest.createGroup('privGroup', 'private group', false));

    it('Test that anonymous loading private group prompts login', function () {
        var privateGroupFragment = Backbone.history.fragment;
        girderTest.anonymousLoadPage(true, privateGroupFragment, true, girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!'));
    });

    it('go back to groups page', girderTest.goToGroupsPage());

    it('Create a public group',
        girderTest.createGroup('pubGroup', 'public group', true));

    it('Open edit dialog and check url state', function () {
        waitsFor(function () {
            return $('.g-group-actions-button:visible').length === 1;
        }, 'the group actions button to appear');

        runs(function () {
            $('.g-group-actions-button').click();
        });

        waitsFor(function () {
            return $('.g-edit-group:visible').length === 1;
        }, 'the group edit action to appear');

        runs(function () {
            $('.g-edit-group').click();
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-18) === '/roles?dialog=edit';
        }, 'the url state to change');
        girderTest.waitForDialog();

        waitsFor(function () {
            return $('a.btn-default').text() === 'Cancel';
        }, 'the cancel button to appear');

        runs(function () {
            $('a.btn-default').click();
        });
        girderTest.waitForLoad();
    });

    it('have the admin remove and then force add themself to the group', function () {
        runs(function () {
            $('.g-group-admin-remove').click();
        });

        girderTest.waitForDialog();

        waitsFor(function () {
            return $('#g-confirm-button').text() === 'Yes';
        }, 'the confirmation button to appear');

        // Admin user removes themself from the group
        runs(function () {
            $('#g-confirm-button').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('ul.g-group-members>li').length === 0;
        });

        _invite('admin', 'member', 'add');

        waitsFor(function () {
            return $('ul.g-group-members>li').length === 1;
        }, 'admin user to appear in the member list');
    });

    it('check that logging out of a group redirects to the front page', function () {
        girderTest.logout()();
        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });

    it('check that logging out of the groups list page redirects to the front page', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();
        girderTest.goToGroupsPage()();
        girderTest.logout()();
        waitsFor(function () {
            return $('.g-frontpage-title:visible').length > 0;
        }, 'front page to display');
    });

    it('check that the groups page has both groups for admin', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();
        girderTest.goToGroupsPage()();
        waitsFor(function () {
            return $('.g-group-list-entry').length === 2;
        }, 'the two groups to show up');

        runs(function () {
            expect($('.g-group-list-entry').text().match('privGroup').length === 1);
            expect($('.g-group-list-entry').text().match('pubGroup').length === 1);
            expect($('.g-group-list-entry').text().match('private group').length === 1);
            expect($('.g-group-list-entry').text().match('public group').length === 1);
        });
    });

    it('check that the groups page has only the public groups for anon', function () {
        girderTest.logout()();
        girderTest.goToGroupsPage()();
        waitsFor(function () {
            return $('.g-group-list-entry').length === 1;
        }, 'the two groups to show up');

        runs(function () {
            expect($('.g-group-list-entry').text().match('pubGroup').length === 1);
            expect($('.g-group-list-entry').text().match('public group').length === 1);
            $('.g-group-link:first').click();
        });

        waitsFor(function () {
            return $('.g-group-name').text() === 'pubGroup';
        }, 'the group page to load');
    });

    it('check promotion and demotion', function () {
        girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();
        girderTest.goToGroupsPage()();
        waitsFor(function () {
            return $('.g-group-list-entry').length === 2 &&
                   $('.g-group-list-entry:contains("pubGroup") .g-group-link').length === 1;
        }, 'the two groups to show up');
        runs(function () {
            $('.g-group-list-entry:contains("pubGroup") .g-group-link').click();
        });
        waitsFor(function () {
            return $('.g-group-name').text() === 'pubGroup' &&
                   $('.g-group-mods .g-member-list-empty').length === 1 &&
                   $('.g-group-admins .g-member-list-empty').length === 1 &&
                   $('.g-group-members-body').length === 1 &&
                   $('.g-group-members .g-member-name').length === 1;
        }, 'the group page to load');
        runs(function () {
            $('.g-group-members .g-group-member-controls .dropdown .g-group-member-promote').click();
        });
        waitsFor(function () {
            return $('.g-group-members .g-group-member-controls .g-promote-moderator:visible').length === 1;
        }, 'wait for member drop down dialog to appear');
        runs(function () {
            $('.g-group-members .g-group-member-controls .g-promote-moderator').click();
        });
        waitsFor(function () {
            return $('.g-group-members .g-member-list-empty').length === 1 &&
                   $('.g-group-mods').length === 1 &&
                   $('.g-group-mod-promote').length === 1;
        }, 'the member to become a moderator');
        runs(function () {
            $('.g-group-mod-promote').click();
        });
        waitsFor(function () {
            return $('.g-group-members .g-member-list-empty').length === 1 &&
                   $('.g-group-mods .g-member-list-empty').length === 1 &&
                   $('.g-group-admins').length === 1 &&
                   $('.g-group-admin-demote').length === 1;
        }, 'the member to become an admin');
        runs(function () {
            $('.g-group-admin-demote').click();
        });
        waitsFor(function () {
            return $('.g-group-admins .g-demote-member:visible').length === 1;
        }, 'wait for admin drop down dialog to appear');
        runs(function () {
            $('.g-group-admins .g-demote-moderator').click();
        });
        girderTest.confirmDialog();
        waitsFor(function () {
            return $('.g-group-members .g-member-list-empty').length === 1 &&
                   $('.g-group-admins .g-member-list-empty').length === 1 &&
                   $('.g-group-mods').length === 1 &&
                   $('.g-group-mod-promote').length === 1;
        }, 'the member to become a moderator');
        runs(function () {
            $('.g-group-mod-demote').click();
        });
        girderTest.confirmDialog();
        waitsFor(function () {
            return $('.g-group-admins .g-member-list-empty').length === 1 &&
                   $('.g-group-mods .g-member-list-empty').length === 1 &&
                   $('.g-group-members .g-member-name').length === 1;
        }, 'the member to be a plain member');
        runs(function () {
            $('.g-group-members .g-group-member-controls .dropdown .g-group-member-promote').click();
        });
        waitsFor(function () {
            return $('.g-group-members .g-group-member-controls .g-promote-admin:visible').length === 1;
        }, 'wait for member drop down dialog to appear');
        runs(function () {
            $('.g-group-members .g-group-member-controls .g-promote-admin').click();
        });
        waitsFor(function () {
            return $('.g-group-members .g-member-list-empty').length === 1 &&
                   $('.g-group-mods .g-member-list-empty').length === 1 &&
                   $('.g-group-admins').length === 1 &&
                   $('.g-group-admin-demote').length === 1;
        }, 'the member to become an admin');
        runs(function () {
            $('.g-group-admin-demote').click();
        });
        waitsFor(function () {
            return $('.g-group-admins .g-demote-member:visible').length === 1;
        }, 'wait for admin drop down dialog to appear');
        runs(function () {
            $('.g-group-admins .g-demote-member').click();
        });
        girderTest.confirmDialog();
        waitsFor(function () {
            return $('.g-group-admins .g-member-list-empty').length === 1 &&
                   $('.g-group-mods .g-member-list-empty').length === 1 &&
                   $('.g-group-members .g-member-name').length === 1;
        }, 'the member to be a plain member');
    });

    it('check member addition and removal', function () {
        runs(function () {
            $('.g-group-member-remove').click();
        });
        girderTest.confirmDialog();
        _invite('admin', 'member', 'invite');
        _invite('admin', 'moderator', 'invite');
        _invite('admin', 'admin', 'invite');
        _invite('admin', 'moderator', 'add');
        waitsFor(function () {
            return $('.g-group-members .g-member-list-empty').length === 1 &&
                   $('.g-group-admins .g-member-list-empty').length === 1 &&
                   $('.g-group-mods').length === 1 &&
                   $('.g-group-mod-promote').length === 1;
        }, 'the member to become a moderator');
        runs(function () {
            $('.g-group-mod-remove').click();
        });
        girderTest.confirmDialog();
        _invite('admin', 'admin', 'add');
        waitsFor(function () {
            return $('.g-group-members .g-member-list-empty').length === 1 &&
                   $('.g-group-mods .g-member-list-empty').length === 1 &&
                   $('.g-group-admins').length === 1 &&
                   $('.g-group-admin-demote').length === 1;
        }, 'the member to become an admin');
        runs(function () {
            $('.g-group-admin-remove').click();
        });
        girderTest.confirmDialog();
        _invite('admin', 'admin', 'add');
    });

    it('check ability to directly add users to groups', function () {
        var policyTest = [
            {setting: 'never', user: 1, mayAdd: false},
            {setting: 'nomod', user: 1, mayAdd: false},
            {setting: 'yesadmin', user: 1, mayAdd: true},
            {setting: 'yesadmin', user: 2, mayAdd: false},
            {setting: 'yesadmin', user: 3, mayAdd: null},
            {setting: 'yesmod', user: 2, mayAdd: true},
            {setting: 'never', user: 'admin', mayAdd: true},
            {setting: 'nomod', user: 'admin', mayAdd: true}
        ];
        /* Add a bunch of users to facilitate testing */
        runs(function () {
            for (var i = 1; i <= 3; i += 1) {
                girderTest.logout()();
                girderTest.createUser('user' + i, 'user' + i + '@email.com',
                    'User' + i, 'User', 'password!')();
            }
        });
        /* Use the admin user to force-add certain users to the group */
        runs(function () {
            girderTest.logout()();
            girderTest.login('admin', 'Admin', 'Admin', 'adminpassword!')();
            girderTest.goToGroupsPage()();
            waitsFor(function () {
                return $('.g-group-list-entry').length === 2 &&
                       $('.g-group-list-entry:contains("pubGroup") .g-group-link').length === 1;
            }, 'the two groups to show up');
            runs(function () {
                $('.g-group-list-entry:contains("pubGroup") .g-group-link').click();
            });
            waitsFor(function () {
                return $('.g-group-name').text() === 'pubGroup' &&
                       $('.g-group-members .g-member-list-empty').length === 1 &&
                       $('.g-group-mods .g-member-list-empty').length === 1 &&
                       $('.g-group-admins').length === 1;
            }, 'the group page to load');
            _invite('user1', 'admin', 'add');
            _invite('user2', 'moderator', 'add');
            _invite('user3', 'member', 'add');
        });
        var curUser = 'admin', curSetting = 'never';
        for (var i = 0; i < policyTest.length; i += 1) {
            var policy = policyTest[i];
            _testDirectAdd(policy, curUser, curSetting);
            curUser = policy.user;
            curSetting = policy.setting;
        }
        /* Open and save the group to test that the add-to-group control is
         * shown */
        waitsFor(function () {
            return $('.g-group-actions-button:visible').length === 1;
        }, 'the group actions button to appear');
        runs(function () {
            $('.g-group-actions-button').click();
        });
        waitsFor(function () {
            return $('.g-edit-group:visible').length === 1;
        }, 'the group edit action to appear');
        runs(function () {
            $('.g-edit-group').click();
        });
        girderTest.waitForDialog();
        waitsFor(function () {
            return $('#g-add-to-group').length === 1;
        }, 'the add-to-group control to appear');
        runs(function () {
            $('button.btn-primary').click();
        });
        girderTest.waitForLoad();
    });
});
