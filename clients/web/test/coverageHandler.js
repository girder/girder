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
    var publicApi = {
        handleCoverage: function (cov, userOptions) {
            if (!cov) {
                return false;
            }

            var options = {
                threshold: 50 //defaults to 50%
            };

            if (userOptions) {
                options.threshold = userOptions.threshold || options.threshold;
            }

            var totals = [];
            for (var filename in cov) {
                console.log(filename);
                      var data = cov[filename];
                var reportData = this.reportFile(data, options);
                var linesCovered = reportData[0];
                var linesTotal = reportData[1];
                var percentCovered = reportData[2];
                console.log(linesCovered +" / "+linesTotal +" lines covered; "+percentCovered+"% coverage");
                totals.push(reportData);
            }

            var totalHits = 0;
            var totalSloc = 0;
            totals.forEach(function(elem){
              totalHits += elem[0];
              totalSloc += elem[1];
            });

            var globCoverage = (totalHits === 0 || totalSloc === 0) ?
                                  0 : totalHits / totalSloc * 100;
            console.log("Coverage: "+Math.floor(globCoverage)+"%");

            if (globCoverage < options.threshold || isNaN(globCoverage)){
              console.error("Code coverage below threshold: "+Math.floor(globCoverage)+ " < "+options.threshold);
              if (typeof process !== "undefined"){
                process.exit(1);
              }
              return false;

            }else{
              console.log("Coverage succeeded.");
            }
            return true;
          },
          reportFile: function( data,options) {
            var ret = {
              coverage: 0,
              hits: 0,
              misses: 0,
              sloc: 0
            };
            data.source.forEach(function(line, num){
              num++;
              var coverageLine;
              if (data[num] === 0) {
                ret.misses++;
                ret.sloc++;
                coverageLine = "0";
              } else if (data[num] !== undefined) {
                ret.hits++;
                ret.sloc++;
                coverageLine = data[num];
              } else {
                coverageLine = 'U';
              }
              coverageLine = coverageLine + " " + line;
              console.log(coverageLine);
            });
            ret.coverage = ret.hits / ret.sloc * 100;

            return [ret.hits,ret.sloc,ret.coverage];
          }
    };
    return publicApi;
})();
