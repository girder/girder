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
    });
});
