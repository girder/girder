girderTest.startApp();

describe('Test version reporting', function () {
    it('check front page version', function () {
        waitsFor(function () {
            return $('.g-frontpage-body').length > 0;
        });

        runs(function () {
            // Better checks are possible, but this at least ensures
            // that the sha isn't 'undefined'.
            expect($('.g-version').length).toBe(1);
            expect(!!$('.g-version')
                .text()
                .trim()
                .toLowerCase()
                .match(/^\d+\.\d+\.\d+/)
            ).toBe(true);
        });
    });
});
