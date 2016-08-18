/* globals girderTest, runs, waitsFor, expect, describe, it */

/**
 * Start the girder backbone app.
 */
girderTest.startApp();

describe('Test empty and default layouts', function () {
    function expectEmptyLayout() {
        // ensure that all components we expect hidden are hidden
        expect($('#g-app-header-container').is(':visible')).toBe(false);
        expect($('#g-global-nav-container').is(':visible')).toBe(false);
        expect($('#g-app-footer-container').is(':visible')).toBe(false);
        // ensure the empty layout is present
        expect($('#g-app-body-container').hasClass('g-empty-layout')).toBe(true);
        // and the default layout is absent
        expect($('#g-app-body-container').hasClass('g-default-layout')).toBe(false);
        // test that body elements remain visible
        expect($('.g-collection-create-button').is(':visible')).toBe(true);
    }

    function expectDefaultLayout() {
        // ensure that all components we expect revealed are visible
        expect($('#g-app-header-container').is(':visible')).toBe(true);
        expect($('#g-global-nav-container').is(':visible')).toBe(true);
        expect($('#g-app-footer-container').is(':visible')).toBe(true);
        // ensure the default layout is present
        expect($('#g-app-body-container').hasClass('g-default-layout')).toBe(true);
        // and the empty layout is absent
        expect($('#g-app-body-container').hasClass('g-empty-layout')).toBe(false);
        // test that body elements remain visible
        expect($('.g-collection-create-button').is(':visible')).toBe(true);
    }

    girder.router.route('collections/emptylayout', 'collectionsEmptyLayout', function (params) {
        girder.events.events.trigger('g:navigateTo', girder.views.body.CollectionsView, params || {}, {layout: girder.constants.Layout.EMPTY});
    });

    girder.router.route('collections/defaultlayout', 'collectionsDefaultLayout', function (params) {
        girder.events.events.trigger('g:navigateTo', girder.views.body.CollectionsView, params || {}, {layout: girder.constants.Layout.DEFAULT});
    });

    it('register a user (first is admin)',
        girderTest.createUser('admin',
                              'admin@email.com',
                              'Admin',
                              'Admin',
                              'adminpassword!'));

    it('go to collections empty layout page', function () {
        waitsFor(function () {
            return $('#g-app-header-container').is(':visible');
        }, 'wait for app header container to appear so we can know it will disappear');

        girderTest.testRoute('collections/emptylayout', false, function () {
            // go to emptylayout, be sure that app header is gone
            return $('#g-app-header-container').is(':visible') === false;
        });

        runs(expectEmptyLayout);
    });

    it('go to standard collections page, test that not passing a layout will revert to default', function () {
        girderTest.testRoute('collections', false, function () {
            // route back to the standard collections view, this should
            // revert to the default layout
            // be sure that app header is back
            return $('#g-app-header-container').is(':visible') === true;
        });

        runs(expectDefaultLayout);
    });

    it('go to collections empty layout page, then specify a default layout', function () {
        // previously we tested setting a layout to empty, then letting app.js
        // revert to the default layout when none is specified
        //
        // this will test setting a layout to empty, and then specifying a default layout
        // to test the additional code path

        waitsFor(function () {
            return $('#g-app-header-container').is(':visible');
        }, 'wait for app header container to appear so we can know it will disappear');

        girderTest.testRoute('collections/emptylayout', false, function () {
            // go to emptylayout, be sure that app header is gone
            return $('#g-app-header-container').is(':visible') === false;
        });

        runs(expectEmptyLayout);

        girderTest.testRoute('collections/defaultlayout', false, function () {
            // this should revert to the default layout
            // be sure that app header is back
            return $('#g-app-header-container').is(':visible') === true;
        });

        runs(expectDefaultLayout);
    });
});
