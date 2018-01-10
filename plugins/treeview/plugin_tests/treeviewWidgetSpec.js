girderTest.importPlugin('treeview');
girderTest.startApp();

var user;
beforeEach(function () {
    user = girder.auth.getCurrentUser();
});

function selectNode(el) {
    return $(el).children('a').click();
}

function expandNode(el) {
    $(el).children('i').click();
    return $(el).children('ul');
}

function waitForTree(el) {
    var ready = false;
    var bound = false;
    waitsFor(function () {
        if (!bound && $(el).length) {
            $(el).one('ready.jstree', function () {
                ready = true;
            });
            bound = true;
        }
        return ready;
    }, 'jstree to load');
}

describe('Setup', function () {
    it('login', girderTest.login('admin', 'First', 'Last', 'password'));
    it('browse to treeview config page', function () {
        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]:visible').length > 0;
        }, 'admin nav link to appear');

        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });

        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'navigate to admin page');

        runs(function () {
            $('.g-plugins-config').click();
        });

        waitsFor(function () {
            return $('.g-plugin-config-link[g-route="plugins/treeview/config"]').length > 0;
        }, 'navigate to plugins page');

        runs(function () {
            $('.g-plugin-config-link[g-route="plugins/treeview/config"]').click();
        });

        waitForTree('.g-treeview-container');
    });
});

describe('TreeView widget', function () {
    describe('Home', function () {
        it('Show home document', function () {
            runs(function () {
                var el = selectNode('#' + user.id);
                expect(el.text()).toBe('Home');
            });

            girderTest.waitForLoad();

            runs(function () {
                var json = JSON.parse($('pre.g-treeview-selected').text());
                expect(json.id).toBe(user.id);
            });
        });
        it('Expand home document', function () {
            expandNode('#' + user.id);
        });
    });
});
