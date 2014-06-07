/**
 * Contains utility functions used in the girder jasmine tests.
 */
var girderTest = girderTest || {};

window.alert = function (msg) {
    // alerts block phantomjs and will destroy us.
    console.log(msg);
};

// Timeout to wait for asynchronous actions
girderTest.TIMEOUT = 5000;
