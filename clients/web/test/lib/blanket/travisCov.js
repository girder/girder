(typeof exports !== "undefined" ? exports : window).travisCov = (function(){
    var main = {
      check: function(cov,userOptions){
        if (!cov){
          return false;
        }
        
        var options = {
          threshold: 50 //defaults to 50%
        };

        if (userOptions){
          options.threshold = userOptions.threshold || options.threshold;
        }

        var totals =[];
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
return true;
	if (globCoverage < options.threshold || isNaN(globCoverage)){
          console.log("Code coverage below threshold: "+Math.floor(globCoverage)+ " < "+options.threshold);
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
  return main;
})();
