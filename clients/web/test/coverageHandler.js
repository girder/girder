/**
 * Copyright Kitware Inc.
 *
 * This is the coverage handler that iterates over our blanket output and
 * writes it out in the desired format. This runs within the inner test app
 * environment after the jasmine spec run is complete. The first argument
 * to coverageHandler.handleCoverage() should be the coverage data object.
 * The second argument is an object specifying the options. These options may
 * contain:
 *  - threshold: An integer value representing the minimum coverage percentage
 *               required to be successful. Coverage below the threshold
 *               causes an error message to be printed and the function to
 *               return false.
 * handleCoverage() returns true in the case of success, and false otherwise.
 */
window.coverageHandler = (function () {
    /**
     * Helper to get the coverage results for an individual file.
     * @param data The per-file value from blanket
     * @param overall The object to write overall coverage data back to.
     */
    var _getDataForFile = function (data, overall) {
        var ret = {
            hits: 0,
            sloc: 0,
            lines: {}
        };
        data.source.forEach(function (line, num) {
            num++;
            var coverageLine;
            if (data[num] === 0) {
                ret.sloc++;
                ret.lines[num] = 0;
            } else if (data[num] !== undefined) {
                ret.hits++;
                ret.sloc++;
                ret.lines[num] = 1;
            }
        });
        ret.coverage = ret.sloc > 0 ? (ret.hits / ret.sloc) : 0;

        overall.hits += ret.hits;
        overall.sloc += ret.sloc;

        return ret;
    };

    /**
     * Writes the coverage output as a cobertura-compliant XML file. Flushes
     * the output in chunks to the console with the expecation that it will
     * be consumed and written to a file by the containing environment.
     * @param perFile The perfile data built by _getDataForFile.
     * @param overall The overage coverage values.
     */
    var _writeOutputXml = function (perFile, overall) {
        console.log('<?xml version="1.0" ?>\n<!DOCTYPE coverage SYSTEM ' +
            '\'http://cobertura.sourceforge.net/xml/coverage-03.dtd\'>\n');
        console.log('<coverage branch-rate="0" line-rate="' + overall.coverage +
            '" timestamp="' + new Date().getTime() + '" version="3.6">\n' +
            '\t<packages>\n\t\t<package name="" branch-rate="0" complexity="0"' +
            'line-rate="' + overall.coverage + '">\n\t\t\t<classes>\n');

        _.each(perFile, function (data, filename) {
            var fileXml = '\t\t\t\t<class branch-rate="0" complexity="0" ' +
                'filename="' + filename + '" line-rate="' + data.coverage.toFixed(3) +
                '" name="' + filename + '">\n\t\t\t\t\t<methods />\n' +
                '\t\t\t\t\t<lines>\n';

            _.each(data.lines, function (val, lineNum) {
                fileXml += '\t\t\t\t\t\t<line hits="' + val + '" number="' +
                    lineNum + '" />\n';
            });

            fileXml += '\t\t\t\t\t</lines>\n\t\t\t\t</class>\n';
            console.log(fileXml);
        });

        console.log('\t\t\t</classes>\n\t\t</package>\n\t</packages>\n</coverage>\n');
    };

    var publicApi = {
        handleCoverage: function (cov, userOptions) {
            if (!cov) {
                return false;
            }

            // Default option values
            var options = {
                threshold: 50
            };

            // User-specified option overrides
            if (userOptions) {
                options.threshold = userOptions.threshold || options.threshold;
            }

            var perFile = {};
            var overall = {
                hits: 0,
                sloc: 0
            };

            _.each(cov, function(data, filename) {
                perFile[filename] = _getDataForFile(data, overall);
            });

            overall.coverage = overall.sloc > 0 ?
                (overall.hits / overall.sloc) : 0;

            _writeOutputXml(perFile, overall);

            return overall.coverage * 100 > options.threshold;
        }
    };
    return publicApi;
})();
