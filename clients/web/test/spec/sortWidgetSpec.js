girderTest.startApp();

var registeredUsers = [];

describe('Sort user list', function () {
    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'BFirstName',
                              'BLastName',
                              'adminpassword!',
                              registeredUsers));
    it('logout', girderTest.logout());

    it('register another user',
        girderTest.createUser('nonadmin',
                              'nonadmin@email.com',
                              'CFirstName',
                              'CLastName',
                              'password!',
                              registeredUsers));
    it('logout', girderTest.logout());

    it('register third user',
        girderTest.createUser('nonadmin2',
                              'nonadmin2@email.com',
                              'AFirstName',
                              'ALastName',
                              'password!',
                              registeredUsers));

    it('view the users on the user page and try different sort options', function () {
        girderTest.goToUsersPage()();
        runs(function () {
            expect($('.g-user-list-entry').length).toBe(3);
            expect($('a.g-user-link').text()).toBe('AFirstName ALastNameBFirstName BLastNameCFirstName CLastName');
            $('a.g-sort-order-button:not(.hide)').click();
        });

        waitsFor(function () {
            return $('a.g-sort-order-button.g-down:not(.hide)').length > 0;
        }, 'switching sort icon');

        runs(function () {
            expect($('a.g-user-link').text()).toBe('CFirstName CLastNameBFirstName BLastNameAFirstName ALastName');
        });

        runs(function () {
            $('.g-collection-sort-actions').click();
        });

        waitsFor(function () {
            return $('.g-collection-sort-menu:visible').length === 1;
        }, 'wait for member drop down dialog to appear');

        runs(function () {
            expect($('a.g-collection-sort-link').text()).toBe('Last NameCreation DateUsed Space');
            expect($('a.g-collection-sort-link:contains("Creation Date")').length).toBe(1);
            $('a.g-collection-sort-link:contains("Creation Date")').click();
        });

        waitsFor(function () {
            // FIXME: the condition here should be: wait for re-render of collection,
            //   but I don't know how to express that...
            return $('.g-user-link').text() === 'AFirstName ALastNameCFirstName CLastNameBFirstName BLastName';
        }, 'refetching and rendering user list');

        runs(function () {
            expect($('a.g-user-link').text()).toBe('AFirstName ALastNameCFirstName CLastNameBFirstName BLastName');
        });
    });
});
