girderTest.importPlugin('candela');
girderTest.startApp();

describe('Test the candela UI.', function () {
    it('register a user', girderTest.createUser(
        'johndoe', 'john.doe@email.com', 'John', 'Doe', 'password!'
    ));

    it('uploads the data file', function () {
        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(0);
            $('.g-user-text>a:first').click();
            expect($('#g-user-action-menu.open').length).toBe(1);
            $('a.g-my-folders').click();
        });

        waitsFor(function () {
            return $('a.g-folder-list-link').length === 2;
        }, 'Public and Private folders to appear');

        runs(function () {
            $('a.g-folder-list-link:contains("Public")').click();
        });
        girderTest.waitForLoad();

        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Public' &&
                   $('.g-empty-parent-message:visible').length === 1;
        }, 'descending into Public folder');

        girderTest.binaryUpload('clients/web/test/testFile.csv');

        runs(function () {
            $('.g-item-list-link:first').click();
        });
    });

    it('sets up candela inputs and renders the visualization', function () {
        waitsFor(function () {
            return $('.g-item-candela-component').length === 1;
        }, 'the candela component selector to appear');

        runs(function () {
            expect($('.g-item-candela-component option').length).toBeGreaterThan(5);
            $('.g-item-candela-component').val('BarChart').change();
        });

        waitsFor(function () {
            var inputs = $('.g-candela-inputs-container').children().eq(1).children().children();
            return inputs.length > 3;
        }, 'the bar chart options to be available');

        runs(function () {
            var inputs = $('.g-candela-inputs-container').children().eq(1).children().children();
            expect(inputs.eq(0).find('label').text()).toBe('Width');
            expect(inputs.eq(1).find('label').text()).toBe('Height');
            expect(inputs.eq(2).find('label').text()).toBe('X');
            var values = [];
            for (var i = 0; i < 4; i += 1) {
                values.push(inputs.eq(2).find('option').eq(i).text());
            }
            values.sort();
            expect(values).toEqual(['(none)', 'a_b', 'c', 'id']);
            $('.g-candela-update-vis').click();
        });

        waitsFor(function () {
            return $('.g-candela-vis').find('canvas').length === 1;
        }, 'the vis canvas to be drawn');

        runs(function () {
            $('.g-item-candela-component').val('TreeHeatmap').change();
        });

        waitsFor(function () {
            var inputs = $('.g-candela-inputs-container').children().eq(1).children().children();
            return inputs.length === 9;
        }, 'the visualization type to change to TreeHeatmap');

        runs(function () {
            var inputs = $('.g-candela-inputs-container').children().eq(1).children().children();
            expect(inputs.eq(2).find('label').text()).toBe('Identifier column');
            expect(inputs.eq(3).find('label').text()).toBe('Color scale');
            expect(inputs.eq(3).find('option').eq(1).text()).toBe('row');
        });

        runs(function () {
            $('.g-item-candela-component').val('Histogram').change();
        });

        waitsFor(function () {
            var inputs = $('.g-candela-inputs-container').children().eq(1).children().children();
            return inputs.length > 3;
        }, 'the visualization type to change to BulletChart');

        runs(function () {
            var inputs = $('.g-candela-inputs-container').children().eq(1).children().children();
            expect(inputs.eq(2).find('label').text()).toBe('X');
        });
    });

    it('uploads a bad data file', function () {
        runs(function () {
            expect($('#g-user-action-menu.open').length).toBe(0);
            $('.g-user-text>a:first').click();
        });
        waitsFor(function () {
            return $('#g-user-action-menu.open').length === 1;
        }, 'menu to open');

        runs(function () {
            $('a.g-my-folders').click();
        });
        waitsFor(function () {
            return $('.g-folder-list-link').length > 0;
        }, 'user folder list to load');

        runs(function () {
            $('a.g-folder-list-link:contains("Public")').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('ol.breadcrumb>li.active').text() === 'Public' &&
                   $('.g-item-list-link').length === 1;
        }, 'descending into Public folder');

        girderTest.binaryUpload('clients/web/test/testFileBad.csv');

        runs(function () {
            $('.g-item-list-link').eq(1).click();
        });

        waitsFor(function () {
            return $('.alert-danger').length === 1;
        }, 'the error message to appear');

        runs(function () {
            expect($('.alert-danger').text()).toContain('An error occurred while attempting to read and parse the data file.');
        });
    });
});
