var PhantomJasmineRunner, addReporter, address,threshold, page, runner;

PhantomJasmineRunner = (function() {
  function PhantomJasmineRunner(page, exit_func) {
    this.page = page;
    this.exit_func = exit_func != null ? exit_func : phantom.exit;
    this.tries = 0;
    this.max_tries = 10;
  }

  PhantomJasmineRunner.prototype.get_status = function() {
    return this.page.evaluate(function (threshold) {
      if (window.jasmine_phantom_reporter.status === "success"){
          return window.travisCov.check(window._$blanket);
      }
      else {
          return false;
      }
    }, threshold);
  };

  PhantomJasmineRunner.prototype.terminate = function() {
      var status = this.get_status();
      if (status) {
          return this.exit_func(0);
      }
      else {
          return this.exit_func(1);
      }
  };

  return PhantomJasmineRunner;

})();

if (phantom.args.length === 0) {
  console.log("Need a url as the argument");
  phantom.exit(1);
}

page = new WebPage();

runner = new PhantomJasmineRunner(page);

page.onConsoleMessage = function(msg) {
  if (output) console.log(msg);
  if (msg === "ConsoleReporter finished") {
    output=true;
    return runner.terminate();
  }
};

var output=true;

address = phantom.args[0];

threshold = phantom.args[1] || 0;

page.onInitialized = function(){
  page.injectJs('travisCov.js');
};

page.open(address, function(status) {
  console.log(address);
  console.log(status);
  if (status !== "success") {
    console.log("can't load the address!");
    phantom.exit(1);
  }


});

