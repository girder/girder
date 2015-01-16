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

describe('Test version reporting', function () {
    it('check front page git SHA', function () {
        waitsFor(function () {
            return $('.g-frontpage-body').length > 0;
        });

        runs(function () {
            // Better checks are possible, but this at least ensures
            // that the sha isn't 'undefined'.
            expect($('.g-git-sha').length).toBe(1);
            expect(!!$('.g-git-sha')
                .text()
                .toLowerCase()
                .match(/^[0-9a-f]+$/)
            ).toBe(true);
        });
    });
});
