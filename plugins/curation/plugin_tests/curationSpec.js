girderTest.addCoveredScripts([
    '/static/built/plugins/curation/templates.js',
    '/plugins/curation/web_client/js/setup.js',
]);

girderTest.importStylesheet(
    '/static/built/plugins/curation/plugin.min.css'
);

girderTest.startApp();

function _goToCurationDialog() {
    girderTest.waitForLoad();
    waitsFor(function () {
        return $('button.g-folder-actions-button:visible').length === 1;
    }, 'folder actions button to be visible');
    runs(function () {
        $('button.g-folder-actions-button:visible').click();
    });
    waitsFor(function () {
        return $('a.g-curation-button:visible').length === 1;
    }, 'curation button to be visible');
    runs(function () {
        $('a.g-curation-button:visible').click();
    });
    waitsFor(function () {
        return $('.g-curation-summary:visible').length === 1;
    }, 'the curation dialog to appear');
}

describe('test the curation ui', function () {
    it('register an admin', girderTest.createUser(
        'admin', 'admin@example.com', 'Joe', 'Admin', 'password'
    ));

    waitsFor(function () {
        return $('a.g-my-folders').length > 0;
    }, 'my folders link to load');
    runs(function () {
        $('a.g-my-folders').click();
    });

    waitsFor(function () {
        return $('a.g-folder-list-link:contains(Public)').length > 0;
    }, 'the folders list to load');
    runs(function () {
        $('a.g-folder-list-link:contains(Public)').click();
    });

    _goToCurationDialog();

    runs(function() {
        expect($('.g-curation-summary:visible').text()).toContain('disabled');
        expect($('#g-curation-enable:visible').length).toBe(1);
        expect($('#g-curation-request:visible').length).toBe(0);
        expect($('#g-curation-approve:visible').length).toBe(0);
        expect($('#g-curation-reject:visible').length).toBe(0);
        expect($('#g-curation-reopen:visible').length).toBe(0);
        expect($('#g-curation-disable:visible').length).toBe(0);
    });
    runs(function () {
        $('#g-curation-enable:visible').click();
    });
    waitsFor(function () {
        return $('.g-curation-summary:visible').length === 0;
    }, 'the curation dialog to disappear');

    _goToCurationDialog();
    runs(function() {
        expect($('.g-curation-summary:visible').text()).toContain('enabled');
        expect($('.g-curation-summary:visible').text()).toContain('construction');
        expect($('#g-curation-enable:visible').length).toBe(0);
        expect($('#g-curation-request:visible').length).toBe(1);
        expect($('#g-curation-approve:visible').length).toBe(0);
        expect($('#g-curation-reject:visible').length).toBe(0);
        expect($('#g-curation-reopen:visible').length).toBe(0);
        expect($('#g-curation-disable:visible').length).toBe(1);
    });

    runs(function () {
        $('#g-curation-request:visible').click();
    });
    waitsFor(function () {
        return $('.g-curation-summary:visible').length === 0;
    }, 'the curation dialog to disappear');

    _goToCurationDialog();
    runs(function() {
        expect($('.g-curation-summary:visible').text()).toContain('enabled');
        expect($('.g-curation-summary:visible').text()).toContain('requested');
        expect($('#g-curation-enable:visible').length).toBe(0);
        expect($('#g-curation-request:visible').length).toBe(0);
        expect($('#g-curation-approve:visible').length).toBe(1);
        expect($('#g-curation-reject:visible').length).toBe(1);
        expect($('#g-curation-reopen:visible').length).toBe(0);
        expect($('#g-curation-disable:visible').length).toBe(1);
    });

    runs(function () {
        $('#g-curation-approve:visible').click();
    });
    waitsFor(function () {
        return $('.g-curation-summary:visible').length === 0;
    }, 'the curation dialog to disappear');

    _goToCurationDialog();
    runs(function() {
        expect($('.g-curation-summary:visible').text()).toContain('enabled');
        expect($('.g-curation-summary:visible').text()).toContain('approved');
        expect($('#g-curation-enable:visible').length).toBe(0);
        expect($('#g-curation-request:visible').length).toBe(0);
        expect($('#g-curation-approve:visible').length).toBe(0);
        expect($('#g-curation-reject:visible').length).toBe(0);
        expect($('#g-curation-reopen:visible').length).toBe(1);
        expect($('#g-curation-disable:visible').length).toBe(1);
    });
});
