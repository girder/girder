girderTest.importPlugin('table_view');
girderTest.startApp();

describe('Test the table UI.', function () {
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

    it('renders the table', function () {
        waitsFor(function () {
            return $('.g-item-table-view-header').length === 1;
        }, 'the table view section header to appear');

        runs(function () {
            $('.g-item-table-view-header').click();
        });

        waitsFor(function () {
            return $('.g-item-table-view-container').length === 1;
        }, 'the table view component selector to appear');

        runs(function () {
            var table = $('.g-item-table-view-container').children().eq(1);
            expect(table.prop('tagName')).toBe('TABLE');
            var headers = table.children().eq(0).children().eq(0).children();
            expect(headers.length === 3);
            var rows = table.children().eq(1).children();
            expect(rows.length === 10);

            // Second page
            $('.g-table-view-page-next').click();
            table = $('.g-item-table-view-container').children().eq(1);
            rows = table.children().eq(1).children();
            expect(rows.length === 5);

            // Still on second page
            $('.g-table-view-page-next').click();
            table = $('.g-item-table-view-container').children().eq(1);
            rows = table.children().eq(1).children();
            expect(rows.length === 5);

            // Back to first page
            $('.g-table-view-page-prev').click();
            table = $('.g-item-table-view-container').children().eq(1);
            rows = table.children().eq(1).children();
            expect(rows.length === 10);

            // Still on first page
            $('.g-table-view-page-prev').click();
            table = $('.g-item-table-view-container').children().eq(1);
            rows = table.children().eq(1).children();
            expect(rows.length === 10);

            // Collapse view
            $('.g-item-table-view-header').click();
            expect($('.g-item-table-view-container').length === 0);

            // Reopen view, should render immediately
            $('.g-item-table-view-header').click();
            table = $('.g-item-table-view-container').children().eq(1);
            rows = table.children().eq(1).children();
            expect(rows.length === 10);
        });
    });

    it('uploads a tab-delimited data file', function () {
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

        girderTest.binaryUpload('clients/web/test/testFile.tsv');

        runs(function () {
            $('.g-item-list-link').eq(1).click();
        });

        waitsFor(function () {
            return $('.g-item-table-view-header').length === 1;
        }, 'the table view section header to appear');

        runs(function () {
            $('.g-item-table-view-header').click();
        });

        waitsFor(function () {
            return $('.g-item-table-view-container').length === 1;
        }, 'the table view component selector to appear');

        runs(function () {
            var table = $('.g-item-table-view-container').children().eq(1);
            expect(table.prop('tagName')).toBe('TABLE');
            var headers = table.children().eq(0).children().eq(0).children();
            expect(headers.length === 3);
            var rows = table.children().eq(1).children();
            expect(rows.length === 2);
        });
    });

    // This test is skipped because this failure mode no longer exists with the
    // updated Candela plugin backing technologies. Specifically, d3-dsv is used
    // for parsing, and that module happily accepts any stream of bytes and will
    // simply parse what it gets, even if that is a zip file or a PNG image or
    // anything else.
    xit('uploads a bad data file', function () {
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
                   $('.g-item-list-link').length === 2;
        }, 'descending into Public folder');

        girderTest.binaryUpload('clients/web/test/testFileBad.csv');

        runs(function () {
            $('.g-item-list-link').eq(2).click();
        });

        waitsFor(function () {
            return $('.g-item-table-view-header').length === 1;
        }, 'the table view section header to appear');

        runs(function () {
            $('.g-item-table-view-header').click();
        });

        waitsFor(function () {
            return $('.g-item-table-view-subtitle').text().length > 20;
        }, 'the error message to appear');

        runs(function () {
            expect($('.g-item-table-view-subtitle').text()).toContain('An error occurred while attempting to read and parse the data file');
        });
    });
});
