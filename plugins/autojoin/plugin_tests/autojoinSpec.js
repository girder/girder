girderTest.importPlugin('autojoin');
girderTest.startApp();

describe('test the autojoin ui', function () {
    it('register an admin', girderTest.createUser(
        'admin', 'admin@girder2.test', 'Joe', 'Admin', 'password'
    ));

    var group1, group2, group3;

    it('go to groups page', girderTest.goToGroupsPage());
    it('create a group', girderTest.createGroup('group1', '', false));
    it('assign group 1', function () {
        group1 = window.location.hash.split('/')[1];
    });

    it('go to groups page', girderTest.goToGroupsPage());
    it('create a group', girderTest.createGroup('group2', '', false));
    it('assign group 2', function () {
        group2 = window.location.hash.split('/')[1];
    });

    it('go to groups page', girderTest.goToGroupsPage());
    it('create a group', girderTest.createGroup('group3', '', false));

    it('assign group 3', function () {
        group3 = window.location.hash.split('/')[1];
    });

    it('go to auto join plugin settings', function () {
        waitsFor(function () {
            return $('a[g-target="admin"]:visible').length > 0;
        }, 'admin console link to display');

        runs(function () {
            $('a[g-target="admin"]:visible').trigger('click');
        });

        waitsFor(function () {
            return $('.g-plugins-config:visible').length > 0;
        }, 'admin console to display');

        runs(function () {
            $('.g-plugins-config:visible').trigger('click');
        });

        waitsFor(function () {
            return $('a[g-route="plugins/autojoin/config"]:visible').length > 0;
        }, 'plugins page to display');

        runs(function () {
            $('a[g-route="plugins/autojoin/config"]:visible').trigger('click');
        });

        waitsFor(function () {
            return $('#g-autojoin-group>option').length === 4;
        }, 'group dropdown to appear');
    });

    it('create auto join rules', function () {
        runs(function () {
            $('#g-autojoin-pattern').val('@girder1.test');
            $('#g-autojoin-group').val(group1);
            $('#g-autojoin-level').val(2);
            $('#g-autojoin-add').trigger('click');

            $('#g-autojoin-pattern').val('@girder2.test');
            $('#g-autojoin-group').val(group2);
            $('#g-autojoin-level').val(1);
            $('#g-autojoin-add').trigger('click');

            $('#g-autojoin-pattern').val('@girder2.test');
            $('#g-autojoin-group').val(group3);
            $('#g-autojoin-level').val(0);
            $('#g-autojoin-add').trigger('click');

            $('#g-autojoin-save').trigger('click');
        });
        waitsFor(function () {
            return $('#g-alerts-container').text().indexOf('Settings saved') !== -1;
        }, 'settings to be saved');
    });

    it('logout', girderTest.logout());
    it('register a user', girderTest.createUser(
        'user1', 'user1@girder2.test', 'Joe', 'User', 'password'
    ));
    it('go to groups page', girderTest.goToGroupsPage());
    it('verify correct groups', function () {
        expect($('.g-group-title:contains("group1")').length).toBe(0);
        expect($('.g-group-title:contains("group2")').length).toBe(1);
        expect($('.g-group-title:contains("group3")').length).toBe(1);
    });

    it('logout', girderTest.logout());
    it('register a user', girderTest.createUser(
        'user2', 'user2@girder1.test', 'Joe', 'User', 'password'
    ));
    it('go to groups page', girderTest.goToGroupsPage());
    it('verify correct groups', function () {
        expect($('.g-group-title:contains("group1")').length).toBe(1);
        expect($('.g-group-title:contains("group2")').length).toBe(0);
        expect($('.g-group-title:contains("group3")').length).toBe(0);
    });
});
