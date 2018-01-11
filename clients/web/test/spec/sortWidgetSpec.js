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
            var defaultOrder = /.*AFirstName.*ALastName.*BFirstName.*BLastName.*CFirstName.*CLastName.*/;
            expect($('a.g-user-link').text()).toMatch(defaultOrder);
            $('a.g-sort-order-button:not(.hide)').click();
        });

        waitsFor(function () {
            return $('a.g-sort-order-button.g-down:not(.hide)').length > 0;
        }, 'switching sort order via icon');

        runs(function () {
            var reversedDefaultOrder = /.*CFirstName.*CLastName.*BFirstName.*BLastName.*AFirstName.*ALastName.*/;
            expect($('a.g-user-link').text()).toMatch(reversedDefaultOrder);
        });

        runs(function () {
            $('.g-collection-sort-actions').click();
        });

        waitsFor(function () {
            return $('.g-collection-sort-menu:visible').length === 1;
        }, 'wait for member drop down dialog to appear');

        runs(function () {
            expect($('a.g-collection-sort-link:contains("Creation Date")').length).toBe(1);
            $('a.g-collection-sort-link:contains("Creation Date")').click();
        });

        waitsFor(function () {
            // FIXME: the condition here should be: wait for re-render of collection,
            //   but I don't know how to express that...
            var sortedByCreationDate = /.*AFirstName.*ALastName.*CFirstName.*CLastName.*BFirstName.*BLastName.*/;
            return sortedByCreationDate.test($('.g-user-link').text());
        }, 'refetching and rendering user list');

        runs(function () {
            var sortedByCreationDate = /.*AFirstName.*ALastName.*CFirstName.*CLastName.*BFirstName.*BLastName.*/;
            expect($('a.g-user-link').text()).toMatch(sortedByCreationDate);
        });
    });
});
