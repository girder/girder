/**
 * Contains utility functions used in the girder jasmine tests.
 */
var girderTest = girderTest || {};

window.alert = function (msg) {
    // alerts block phantomjs and will destroy us.
    console.log(msg);
};

// Timeout to wait for asynchronous actions
girderTest.TIMEOUT = 5000;

girderTest.createUser = function (login, email, firstName, lastName, password) {

    return function () {
        runs(function () {
            expect(girder.currentUser).toBe(null);
        });

        waitsFor(function () {
            return $('.g-register').length > 0;
        }, 'girder app to render');

        runs(function () {
            $('.g-register').click();
        });

        waitsFor(function () {
            return $('input#g-email').length > 0;
        }, 'register dialog to appear');

        runs(function () {
            $('#g-login').val(login);
            $('#g-email').val(email);
            $('#g-firstName').val(firstName);
            $('#g-lastName').val(lastName);
            $('#g-password,#g-password2').val(password);
            $('#g-register-button').click();
        });

        waitsFor(function () {
            return $('.g-user-text a')[0].text === firstName + ' ' + lastName;
        }, 'user to be logged in');

        runs(function () {
            expect(girder.currentUser).not.toBe(null);
            expect(girder.currentUser.name()).toBe(firstName + ' ' + lastName);
            expect(girder.currentUser.get('login')).toBe(login);
        });
    };
};

girderTest.login = function (login, firstName, lastName, password) {

    return function () {
        runs(function () {
            expect(girder.currentUser).toBe(null);
        });

        waitsFor(function () {
            return $('.g-login').length > 0;
        }, 'girder app to render');

        runs(function () {
            $('.g-login').click();
        });

        waitsFor(function () {
            return $('input#g-login').length > 0;
        }, 'register dialog to appear');

        runs(function () {
            $('#g-login').val(login);
            $('#g-password').val(password);
            $('#g-login-button').click();
        });

        waitsFor(function () {
            return $('.g-user-text a')[0].text === firstName + ' ' + lastName;
        }, 'user to be logged in');

        runs(function () {
            expect(girder.currentUser).not.toBe(null);
            expect(girder.currentUser.name()).toBe(firstName + ' ' + lastName);
            expect(girder.currentUser.get('login')).toBe(login);
        });
    };
};

girderTest.logout = function () {

    return function () {
        runs(function () {
            expect(girder.currentUser).not.toBe(null);
        });

        waitsFor(function () {
            return $('.g-logout').length > 0;
        }, 'logout link to render');

        runs(function () {
            $('.g-logout').click();
        });

        waitsFor(function () {
            return $('.g-login').length > 0;
        }, 'login link to appear');
    };
};

girderTest.goToCurrentUserSettings = function () {

    return function () {
        runs(function () {
            expect(girder.currentUser).not.toBe(null);
        });

        waitsFor(function () {
            return $('.g-my-settings').length > 0;
        }, 'my account link to render');

        runs(function () {
            $('.g-my-settings').click();
        });

        waitsFor(function () {
            return $('input#g-email').length > 0;
        }, 'email input to appear');

        runs(function () {
            expect($('input#g-email').val()).toBe(girder.currentUser.get('email'));
            expect($('input#g-firstName').val()).toBe(girder.currentUser.get('firstName'));
            expect($('input#g-lastName').val()).toBe(girder.currentUser.get('lastName'));
        });
    };
};

// This assumes that you're logged into the system and on the create collection
// page.
girderTest.createCollection = function (collName, collDesc) {

    return function () {

        waitsFor(function () {
            return $('li.active .g-page-number').text() === 'Page 1' &&
                   $('.g-collection-create-button').is(':enabled');
        }, 'create collection button to appear');

        waits(500);

        runs(function () {
            $('.g-collection-create-button').click();
        });

        waitsFor(function () {
            return Backbone.history.fragment.slice(-14) === '?dialog=create';
        }, 'url state to change indicating a creation dialog');

        waitsFor(function () {
            return $('input#g-name').length > 0 &&
                   $('.g-save-collection:visible').is(':enabled');
        }, 'create collection dialog to appear');

        runs(function () {
            $('#g-name').val(collName);
            $('#g-description').val(collDesc);
            $('.g-save-collection').click();
        });

        waitsFor(function () {
            return $('.g-collection-name').text() === collName &&
                   $('.g-collection-description').text() === collDesc;
        }, 'new collection page to load');
    };
};

// Go to groups page
girderTest.goToGroupsPage = function () {

    return function () {

        waits(1000);

        waitsFor(function () {
            return $("a.g-nav-link[g-target='groups']:visible").length > 0;
        }, 'groups nav link to appear');

        runs(function () {
            $("a.g-nav-link[g-target='groups']").click();
        });

        waitsFor(function () {
            return $(".g-group-search-form .g-search-field:visible").is(':enabled');
        }, 'navigate to groups page');
    };

};

// Go to users page
girderTest.goToUsersPage = function () {

    return function () {

        waits(1000);

        waitsFor(function () {
            return $("a.g-nav-link[g-target='users']:visible").length > 0;
        }, 'users nav link to appear');

        runs(function () {
            $("a.g-nav-link[g-target='users']").click();
        });

        waitsFor(function () {
            return $(".g-user-search-form .g-search-field:visible").is(':enabled');
        }, 'navigate to users page');
    };

};

// This assumes that you're logged into the system and on the groups page.
girderTest.createGroup = function (groupName, groupDesc, public) {

    return function () {

        waits(1000);

        waitsFor(function () {
            return $('li.active .g-page-number').text() === 'Page 1' &&
                   $('.g-group-create-button:visible').is(':enabled');
        }, 'create group button to appear');

        runs(function () {
            $('.g-group-create-button').click();
        });

        waitsFor(function () {
            return $('#g-dialog-container').hasClass('in') &&
                   $('#g-access-public:visible').length > 0 &&
                   $('#g-name:visible').length > 0 &&
                   $('#g-description:visible').length > 0 &&
                   $('.g-save-group:visible').length > 0;
        }, 'create group dialog to appear');

        if (public) {
            runs(function () {
                $('#g-access-public').click();
            });

            waitsFor(function () {
                return $('.g-save-group:visible').length > 0 &&
                       $('.radio.g-selected').text().match("Public").length > 0;
            }, 'access selection to be set to public');
        }

        runs(function () {
            $('#g-name').val(groupName);
            $('#g-description').val(groupDesc);
            $('.g-save-group').click();
        });

        waitsFor(function () {
            return $('.g-group-name').text() === groupName &&
                   $('.g-group-description').text() === groupDesc;
        }, 'new group page to load');
    };
};
