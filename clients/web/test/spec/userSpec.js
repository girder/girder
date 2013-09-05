

/*
// include the helpers and get a reference to it's exports variable
global.initDOM = function () {
    jsdom = require('jsdom');
    jQuery = require('jquery').create();
    global.jQuery = global.$ = jQuery;
    window = jsdom.jsdom().createWindow('<html><body></body></html>');
    window.jQuery = jQuery;
    global.document = window.document;
    global.addEventListener = window.addEventListener;
}

// in spec_runner.js
global.initBackbone = function () {
    global.initDOM();
    global.Backbone = require('backbone');
    //global.Backbone.setDomLibrary(jQuery);
    global.Backbone.$ = jQuery; // replaces the above line
    var libs = require('../static/built/libs.min.js');
    var underscore = require('underscore');
    global._ = underscore;

    // probably shouldn't include the source
    // there is a probem with girder.App being undefined
    //var init = require('../src/init.js');
    //var user = require('../src/models/UserModel.js');
    // when try to include app, the alert fires
    var app = require('../static/built/app.min.js');
}
//- See more at: http://blog.rjzaworski.com/2012/07/testing-with-node-jasmine-and-require-js-part-ii/#sthash.efFIWV9B.dpuf
//
//

*/



// include the helpers and get a reference to it's exports variable
// var helpers = require('./TestHelpers');  <!-- include source files here... -->
 /* <script type="text/javascript" src="static/built/libs.min.js"></script>
  <script type="text/javascript" src="src/init.js"></script>
  <script type="text/javascript" src="src/models/UserModel.js"></script>

//#  <!-- include spec files here... -->
  <script type="text/javascript" src="spec/UserSpec.js"></script>
*/
//console.log(helpers);//
//
describe('UserModel Testing', function () {
//    initBackbone()
    it('is defined', function () {
        var user = new girder.models.UserModel();
        expect(user).toBeDefined();
    });
});
