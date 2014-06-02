/**
 * Copyright Kitware Inc.
 *
 * This is the coverage handler that iterates over our blanket output and
 * writes it out in an intermediate format that will be consumed after all the
 * tests have run and combined for reporting.
 */
window.coverageHandler = (function () {
    /**
     * Transforms the source file name from a full path to a path relative
     * to the root of the repository for portability.
     */
    var _transformFilename = function (filename) {
        return filename.substring(filename.indexOf('clients/web/'));
    };

    var publicApi = {
        handleCoverage: function (cov) {
            if (!cov) {
                return false;
            }

            _.each(cov, function (data, filename) {
                var shortFilename = _transformFilename(filename);
                var lines = '';
                console.log('F' + shortFilename + '\n');
                delete data.source;
                _.each(data, function (hits, lineNum) {
                    lines += 'L' + lineNum + ' ' + hits + '\n';
                });
                console.log(lines);
            });

            return true;
        }
    };
    return publicApi;
})();
