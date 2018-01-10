girderTest.importPlugin('homepage');
girderTest.startApp();

function _goToHomepagePluginSettings() {
    waitsFor(function () {
        return $('a[g-target="admin"]:visible').length > 0;
    }, 'admin console link to display');

    runs(function () {
        $('a[g-target="admin"]:visible').click();
    });

    waitsFor(function () {
        return $('.g-plugins-config:visible').length > 0;
    }, 'admin console to display');

    runs(function () {
        $('.g-plugins-config:visible').click();
    });

    waitsFor(function () {
        return $('a[g-route="plugins/homepage/config"]:visible').length > 0;
    }, 'plugins page to display');

    runs(function () {
        $('a[g-route="plugins/homepage/config"]:visible').click();
    });

    waitsFor(function () {
        return $('.g-homepage-container:visible').length > 0;
    }, 'homepage config to display');

    waitsFor(function () {
        return girder.rest.numberOutstandingRestRequests() === 0;
    }, 'rest requests to finish');
}

function _verifyMarkdownContent(elem) {
    expect(elem.find('p:contains("It\'s very easy")').length).toBe(1);
    expect(elem.find('strong:contains("bold")').length).toBe(1);
    expect(elem.find('em:contains("italic")').length).toBe(1);
    expect(elem.find('a[href="https://girder.readthedocs.io/"]:contains("link to Girder!")').length).toBe(1);
}

function _verifyHomepageSettings(elem) {
    expect(elem.find('div[class="g-frontpage-title"]:contains("Header")').length).toBe(1);
    expect(elem.find('div[class="g-frontpage-subtitle"]:contains("Subheader")').length).toBe(1);
    _verifyMarkdownContent(elem);
}

describe('homepage plugin test', function () {
    it('registers an admin user', girderTest.createUser(
        'admin', 'admin@example.com', 'Mark', 'Down', 'password'
    ));

    it('goes to homepage plugin settings', _goToHomepagePluginSettings);

    it('sets, previews, and saves homepage markdown content', function () {
        runs(function () {
            $('.g-homepage-container textarea.g-markdown-text').val(
                'It\'s very easy to make some words **bold** and other words *italic* with ' +
                    'Markdown. You can even [link to Girder!](https://girder.readthedocs.io/)'
            );

            $('.g-homepage-container a.g-preview-link').click();

            _verifyMarkdownContent($('.g-markdown-preview'));

            $('#g-alerts-container').empty();
            $('#g-homepage-form').submit();
        });

        waitsFor(function () {
            return $('.alert:contains("Settings saved.")').length > 0;
        }, 'settings to save');
    });

    it('verifies homepage content as admin user', function () {
        runs(function () {
            $('.g-app-title').click();
        });

        waitsFor(function () {
            return girder.rest.numberOutstandingRestRequests() === 0;
        }, 'rest requests to finish');

        runs(function () {
            _verifyMarkdownContent($('#g-app-body-container'));
        });
    });

    it('goes back to homepage plugin settings', _goToHomepagePluginSettings);

    it('verifies previously set homepage markdown content', function () {
        runs(function () {
            expect($('.g-homepage-container textarea.g-markdown-text').val()).toEqual(
                'It\'s very easy to make some words **bold** and other words *italic* with ' +
                'Markdown. You can even [link to Girder!](https://girder.readthedocs.io/)'
            );
        });
    });

    it('logs out admin', girderTest.logout());

    it('verifies homepage content as anonymous user', function () {
        runs(function () {
            _verifyMarkdownContent($('#g-app-body-container'));
        });
    });

    it('login an admin user', girderTest.login('admin', 'Mark', 'Down', 'password'));

    it('goes to homepage plugin settings', _goToHomepagePluginSettings);

    it('unset homepage markdown content', function () {
        runs(function () {
            $('.g-homepage-container textarea.g-markdown-text').val('');

            $('.g-homepage-container a.g-preview-link').click();

            expect($('.g-homepage-container .g-markdown-preview').text()).toBe('Nothing to show\n');

            $('#g-alerts-container').empty();
            $('#g-homepage-form').submit();
        });

        waitsFor(function () {
            return $('.alert:contains("Settings saved.")').length > 0;
        }, 'settings to save');
    });

    it('sets, previews and saves homepage settings', function () {
        runs(function () {
            $('#g-homepage-header').val('Header');

            $('#g-homepage-subheader').val('Subheader');

            $('.g-homepage-welcome-text-container textarea.g-markdown-text').val(
                'It\'s very easy to make some words **bold** and other words *italic* with ' +
                'Markdown. You can even [link to Girder!](https://girder.readthedocs.io/)'
            );

            $('.g-homepage-welcome-text-container a.g-preview-link').click();

            _verifyMarkdownContent($('.g-homepage-welcome-text-container .g-markdown-preview'));

            $('#g-alerts-container').empty();
            $('#g-homepage-form').submit();
        });

        waitsFor(function () {
            return $('.alert:contains("Settings saved.")').length > 0;
        }, 'settings to save');
    });

    it('verifies homepage content as admin user', function () {
        runs(function () {
            $('.g-app-title').click();
        });

        waitsFor(function () {
            return girder.rest.numberOutstandingRestRequests() === 0;
        }, 'rest requests to finish');

        runs(function () {
            _verifyHomepageSettings($('#g-app-body-container'));
        });
    });

    it('logs out admin', girderTest.logout());

    it('verifies homepage content as anonymous user', function () {
        runs(function () {
            _verifyHomepageSettings($('#g-app-body-container'));
        });
    });
});
