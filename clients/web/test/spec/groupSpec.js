/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after');
});

/* Search for a name on the members search panel, and invite or add the first
 * found user as a member, moderator, or admin.
 *
 * @param name: name to search for.
 * @param level: 'member', 'moderator', or 'admin'.
 * @param action: 'invite' or 'add.
 */
function _invite(name, level, action) {
    // Search for the named user in user search box
    runs(function () {
        $('.g-group-invite-container input.g-search-field')
            .val(name).trigger('input');
    });
    girderTest.waitForLoad();
    waitsFor(function () {
        return $('.g-group-invite-container .g-search-results').hasClass('open');
    }, 'search to return');
    runs(function () {
        var results = $('.g-group-invite-container li.g-search-result');
        expect(results.length).toBe(1);

        expect(results.find('a[resourcetype="user"]').length).toBe(1);

        results.find('a[resourcetype="user"]').click();
    });
    girderTest.waitForDialog();
    waitsFor(function () {
        return $('.g-add-as-member.btn-warning').length === 1;
    }, 'invitation dialog to appear with direct add button');
    runs(function () {
        var sel = 'member';
        switch (level) {
            case 'moderator': sel = 'moderator'; break;
            case 'admin': sel = 'administrarot'; break;
        }
        $('.panel-title:contains("Invite as ' + sel + '") a').click();
    });
    runs(function () {
        $('.g-' + action + '-as-' + level).click();
    });
    girderTest.waitForLoad();
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

    it('have the admin remove and then force add himself to the group', function () {
        runs(function () {
            $('.g-group-admin-remove').click();
        });

        girderTest.waitForDialog();

        waitsFor(function () {
            return $('#g-confirm-button').text() === 'Yes';
        }, 'the confirmation button to appear');

        // Admin user removes himself from the group
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

    it('check that the groups page has both groups for admin', function () {
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
});
