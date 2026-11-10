girderTest.startApp();

describe('Test the storage usage page', function () {
    var privateFolderId;

    it('register an admin', girderTest.createUser(
        'admin', 'admin@girder.test', 'Admin', 'Admin', 'adminpassword!'));

    it('upload a file', function () {
        runs(function () {
            girder.rest.restRequest({
                url: 'folder',
                data: {
                    parentType: 'user',
                    parentId: girder.auth.getCurrentUser().id,
                    name: 'Private'
                }
            }).done(function (resp) {
                privateFolderId = resp[0]._id;
            });
        });
        waitsFor(function () {
            return !!privateFolderId;
        }, 'the private folder to be found');
        runs(function () {
            girder.router.navigate('folder/' + privateFolderId, { trigger: true });
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-upload-here-button').length > 0;
        }, 'the folder to load');
        girderTest.binaryUpload('girder/web_client/test/testFile.txt');
    });

    it('open the usage page of an assetstore', function () {
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').trigger('click');
        });
        waitsFor(function () {
            return $('.g-assetstore-config').length > 0;
        }, 'admin page to load');
        runs(function () {
            $('.g-assetstore-config').trigger('click');
        });
        waitsFor(function () {
            return $('.g-assetstore-container .g-assetstore-usage').length > 0;
        }, 'assetstore page to load');
        runs(function () {
            window.location.hash = $('.g-assetstore-usage').first().attr('href');
        });
        waitsFor(function () {
            return $('.g-usage-children').length > 0;
        }, 'the usage page to load');
        runs(function () {
            expect($('.g-usage-total-size').text()).toContain('6 B');
            expect($('.g-usage-child').length).toBe(1);
            expect($('.g-usage-child').first().text()).toContain('admin');
            expect($('.g-usage-child').first().text()).toContain('User');
            expect($('.g-usage-child .g-usage-open').attr('href')).toMatch(/^#user\//);
            expect($('.g-usage-child .g-usage-open').attr('title')).toBe('Open this user');
            expect($('.g-usage-treemap .g-usage-treemap-rect').length).toBe(1);
            expect($('.g-usage-treemap-rect').first().attr('title')).toBe('admin: 6 B');
            expect($('.g-usage-top-file').length).toBe(1);
            expect($('.g-usage-top-file').text()).toContain('testFile.txt');
            var link = $('.g-usage-top-file .g-usage-file-resource');
            expect(link.attr('href')).toMatch(/^#item\//);
            expect(link.text()).toBe('/user/admin/Private/testFile.txt');
            expect(link.attr('title')).toBe('/user/admin/Private/testFile.txt');
        });
    });

    it('drill down into storage usage', function () {
        var itemLink;
        // Drill into the user from the table
        runs(function () {
            $('.g-usage-children a.g-usage-drill:contains("admin")').trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-breadcrumbs li.active').text() === 'admin' &&
                $('.g-usage-child').length > 0;
        }, 'the user to be shown');
        runs(function () {
            expect($('.g-usage-child').length).toBe(1);
            expect($('.g-usage-child').first().text()).toContain('Private');
            expect($('.g-usage-child .g-usage-open').attr('href')).toBe(
                '#folder/' + privateFolderId);
        });

        // Drill into the folder by clicking the treemap
        runs(function () {
            $('.g-usage-treemap .g-usage-treemap-rect').first().trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-breadcrumbs li.active').text() === 'Private' &&
                $('.g-usage-child').length > 0;
        }, 'the folder to be shown');
        runs(function () {
            expect($('.g-usage-child').first().text()).toContain('testFile.txt');
            expect($('.g-usage-child').first().text()).toContain('Item');
            itemLink = $('.g-usage-child .g-usage-open').attr('href');
            expect(itemLink).toMatch(/^#item\//);
        });

        // Drill into the item to see its files
        runs(function () {
            $('.g-usage-children a.g-usage-drill:contains("testFile.txt")').trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-breadcrumbs li').length === 4 &&
                $('.g-usage-child').length > 0;
        }, 'the item to be shown');
        runs(function () {
            expect($('.g-usage-child').first().text()).toContain('File');
            expect($('.g-usage-children a.g-usage-drill').length).toBe(0);
            // A file links to its item
            expect($('.g-usage-child .g-usage-open').attr('href')).toBe(itemLink);
            expect($('.g-usage-child .g-usage-open').attr('title')).toBe(
                'Open the item of this file');
            // Files are not drillable in the treemap either
            expect($('.g-usage-treemap-rect.g-usage-drillable').length).toBe(0);
        });
    });

    it('change options', function () {
        // Changing options keeps the current resource
        runs(function () {
            $('#g-usage-dedup').prop('checked', true).trigger('change');
        });
        waitsFor(function () {
            return window.location.hash.indexOf('dedup=true') >= 0 &&
                $('.g-usage-child').length > 0;
        }, 'deduplication to be enabled');
        runs(function () {
            expect($('.g-usage-child').length).toBe(1);
            expect($('.g-usage-breadcrumbs li').length).toBe(4);
            $('#g-usage-source').val('imported').trigger('change');
        });
        waitsFor(function () {
            return window.location.hash.indexOf('source=imported') >= 0 &&
                $('.g-usage-empty').length > 0;
        }, 'only imported files to be shown');

        // Return to the top level with the breadcrumb
        runs(function () {
            $('.g-usage-breadcrumbs a.g-usage-drill').first().trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-breadcrumbs li.active').text() === 'All users and collections' &&
                $('.g-usage-summary').length > 0;
        }, 'the top level to be shown');
        runs(function () {
            expect($('#g-usage-source').val()).toBe('imported');
            expect($('#g-usage-dedup').is(':checked')).toBe(true);
        });
        girderTest.waitForLoad();
    });

    it('show usage of all assetstores', function () {
        runs(function () {
            girder.router.navigate('assetstores', { trigger: true });
        });
        waitsFor(function () {
            return $('.g-usage-all-link:visible').length > 0;
        }, 'the assetstores page to load');
        runs(function () {
            expect($('.g-usage-all-link').hasClass('btn')).toBe(true);
            expect($('.g-usage-all-link').text().trim()).toBe('Usage');
            window.location.hash = $('.g-usage-all-link').attr('href');
        });
        waitsFor(function () {
            return $('.g-usage-child').length > 0;
        }, 'the usage of all assetstores to load');
        runs(function () {
            expect($('#g-usage-assetstore').val()).toBe('');
            expect($('.g-usage-child').first().text()).toContain('admin');
            expect($('.g-usage-computed').text()).toContain('Totals computed');
        });

        // Open a resource from the table
        runs(function () {
            window.location.hash = $('.g-usage-child .g-usage-open').first().attr('href');
        });
        waitsFor(function () {
            return $('.g-user-name').text() === 'Admin Admin';
        }, 'the user page to be shown');
        runs(function () {
            girder.router.navigate('assetstores/usage', { trigger: true });
        });
        waitsFor(function () {
            return $('.g-usage-child').length > 0;
        }, 'the usage of all assetstores to load again');

        // Recompute the totals
        runs(function () {
            $('.g-usage-refresh').trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-child').length > 0;
        }, 'the totals to be recomputed');
        runs(function () {
            expect($('.g-usage-child').first().text()).toContain('admin');
        });
        girderTest.waitForLoad();
    });

    it('summarize children past the limit', function () {
        var publicFolderId, limitOne = true, addAttached = false;
        runs(function () {
            girder.rest.restRequest({
                url: 'folder',
                data: {
                    parentType: 'user',
                    parentId: girder.auth.getCurrentUser().id,
                    name: 'Public'
                }
            }).done(function (resp) {
                publicFolderId = resp[0]._id;
            });
        });
        waitsFor(function () {
            return !!publicFolderId;
        }, 'the public folder to be found');
        runs(function () {
            girder.router.navigate('folder/' + publicFolderId, { trigger: true });
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-upload-here-button').length > 0;
        }, 'the folder to load');
        girderTest.binaryUpload('girder/web_client/test/testFile2');

        // List only the largest child, so the other folder is summarized
        runs(function () {
            $.ajaxPrefilter(function (options) {
                // For GET requests, jQuery has serialized the data, but not yet
                // added it to the url.
                if (limitOne && options.url.indexOf('assetstore/usage') >= 0) {
                    options.data = options.data.replace(/(^|&)limit=\d+/, '$1limit=1');
                }
                // Files can't be attached from the web client, so add them
                // to the response.
                if (addAttached && options.url.indexOf('assetstore/usage') >= 0) {
                    options.dataFilter = function (data) {
                        var usage = JSON.parse(data);
                        usage.children.push({
                            type: 'attached',
                            _id: null,
                            name: 'Attached files',
                            size: 5,
                            count: 1,
                            drillable: false
                        });
                        return JSON.stringify(usage);
                    };
                }
            });
            girder.router.navigate('assetstores/usage', { trigger: true });
        });
        waitsFor(function () {
            return $('.g-usage-refresh').length > 0 && $('.g-usage-summary').length > 0;
        }, 'the usage page to load');
        // Include the new file in the cached totals
        runs(function () {
            $('.g-usage-refresh').trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-children a.g-usage-drill:contains("admin")').length > 0;
        }, 'the totals to be recomputed');
        runs(function () {
            $('.g-usage-children a.g-usage-drill:contains("admin")').trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-breadcrumbs li.active').text() === 'admin' &&
                $('.g-usage-child').length > 0;
        }, 'the user to be shown');
        runs(function () {
            limitOne = false;
            expect($('.g-usage-child').length).toBe(1);
            expect($('.g-usage-other td').first().text()).toBe('1 more folder');
            expect($('.g-usage-treemap-rect').length).toBe(2);
            var more = $('.g-usage-treemap-rect.g-usage-treemap-more');
            expect(more.length).toBe(1);
            expect(more.hasClass('g-usage-drillable')).toBe(false);
            expect(more.attr('title')).toMatch(/^1 more folder: /);
        });

        // Attached files link to the resource they are attached to
        runs(function () {
            addAttached = true;
            $('.g-usage-children a.g-usage-drill').first().trigger('click');
        });
        waitsFor(function () {
            return $('.g-usage-child[g-type="attached"]').length > 0;
        }, 'the folder to be shown');
        runs(function () {
            addAttached = false;
            var link = $('.g-usage-child[g-type="attached"] .g-usage-open');
            expect(link.attr('href')).toMatch(/^#folder\//);
            expect(link.attr('title')).toBe('Open the folder these files are attached to');
            expect($('.g-usage-child[g-type="item"] .g-usage-open').attr('title')).toBe(
                'Open this item');
        });
        girderTest.waitForLoad();
    });

    it('non-admins cannot see storage usage', function () {
        girderTest.logout()();
        girderTest.createUser(
            'johndoe', 'john.doe@girder.test', 'John', 'Doe', 'password!')();
        runs(function () {
            girder.router.navigate('assetstores/usage', { trigger: true });
        });
        waitsFor(function () {
            return $('#g-app-body-container').text().indexOf(
                'Must be logged in as admin to view this page.') >= 0;
        }, 'the admin message to be shown');
    });
});
