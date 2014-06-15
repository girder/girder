/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});

describe('Test collection actions', function () {

    it('register a user (first is admin)',
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
        girderTest.createCollection('collName0', 'coll Desc 0'));

    it('go back to collections page', function () {
        runs(function () {
            $("a.g-nav-link[g-target='collections']").click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button:visible').length > 0;
        }, 'navigate to collections page');

        waitsFor(function () {
            return $('.g-collection-list-entry').length === 1;
        }, 'collection list to appear');

        runs(function () {
            expect($('.g-collection-list-entry').text().match('collName0').length > 0);
        });

    });

    it('create another collection',
        girderTest.createCollection('collName1', 'coll Desc 1'));

    it('make new collection public', function () {

        waits(1000);

        waitsFor(function () {
            return $('.g-collection-actions-button:visible').is(':enabled');
        }, 'collection actions link to appear');

        runs(function () {
            $('.g-collection-actions-button').click();
        });

        waits(1000);

        waitsFor(function () {
            return $(".g-collection-access-control[role='menuitem']:visible").length == 1;
        }, 'access control menu item to appear');

        runs(function () {
            $('.g-collection-access-control').click();
        });

        waits(1000);

        waitsFor(function () {
            return $('#g-dialog-container').hasClass('in') &&
                   $('#g-access-public:visible').is(':enabled');
        }, 'dialog and public access radio button to appear');

        runs(function () {
            $('#g-access-public').click();
        });

        waits(1000);

        waitsFor(function () {
            return $('.g-save-access-list:visible').is(':enabled') &&
                   $('.radio.g-selected').text().match("Public").length > 0;
        }, 'access save button to appear');

        runs(function () {
            $('.g-save-access-list').click();
        });

        waits(1000);

        waitsFor(function () {
            return !$('#g-dialog-container').hasClass('in');
        }, 'access dialog to be hidden');
    });

    it('go back to collections page again', function () {
        runs(function () {
            $("a.g-nav-link[g-target='collections']").click();
        });

        waitsFor(function () {
            return $('.g-collection-create-button').is(':enabled');
        }, 'navigate to collections page');

        waitsFor(function () {
            return $('.g-collection-list-entry').text().match('collName1').length > 0;
        }, 'new collection to appear');

    });

    it('logout to become anonymous', girderTest.logout());

    it('check if public collection is viewable (and ensure private is not)', function () {

        waitsFor(function () {
            return $('li.active .g-page-number').text() === 'Page 1' &&
                   $('.g-collection-list-entry').length === 1;
        }, 'collection list page to reload');

        runs(function () {
            expect($('.g-collection-list-entry').text()).not.toContain('collName0');
        });

        waitsFor(function () {
            return $('.g-collection-list-entry').text().match('collName1').length > 0;
        }, 'collName1 to appear');

    });

});
