/**
 * Start the girder backbone app.
 */
$(function () {
    girder.events.trigger('g:appload.before');
    var app = new girder.App({});
    girder.events.trigger('g:appload.after');
});


describe('Create a user', function () {
    it('register a user', function () {
        expect(girder.currentUser).toBe(null);

        waitsFor(function () {
            return $('.g-register').length > 0;
        }, 'girder app to render', girderTest.TIMEOUT);

        runs(function () {
            $('.g-register').click();
        });

        waitsFor(function () {
            return $('input#g-email').length > 0;
        }, 'register dialog to appear', girderTest.TIMEOUT);
    });
});
