/*global girder:true*/
/*global console:true*/

'use strict';

var _ = require('underscore');
var $ = require('jquery');

/*
 * Initialize global girder object
 */
var girder = girder || {};

/*
 * Some cross-browser globals
 */
if (!window.console) {
    window.console = {
        log: $.noop,
        error: $.noop
    };
}

_.extend(girder, {
    layout: 'default'
});

module.exports = girder;
