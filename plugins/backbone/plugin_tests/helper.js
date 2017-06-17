window.testHelper = {
    login: function () {
        runs(function () {
            girder.auth.login('admin', 'adminpassword');
        });
        waitsFor(function () {
            return girder.auth.getCurrentUser();
        });
    },
    test: function (func) {
        var returned;
        var failed;
        runs(function () {
            func().done(function () {
                returned = true;
            }).fail(function (arg) {
                failed = arg;
            });
        });
        waitsFor(function () {
            if (failed) {
                throw failed;
            }
            return returned;
        }, 'promise to resolve');
    },
    equal: function (a, b, omit) {
        omit = omit || ['created', 'updated'];
        expect(_.omit(a, omit)).toEqual(_.omit(b, omit));
    }
};
