/*global girder:true*/
/*global console:true*/

'use strict';

var $ = require('jquery');
var _ = require('underscore');

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
