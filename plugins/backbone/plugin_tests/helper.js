window.testHelper = {
    login: function () {
        runs(function () {
            girder.auth.login('admin', 'adminpassword');
        });
        waitsFor(function () {
            return girder.auth.getCurrentUser();
        });
    }
};
