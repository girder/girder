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

/**
 * The old "jade.templates" namespace is deprecated as of version 1.1, but is
 * retained here for backward compatibility. It will be removed in version 2.0.
 */
/* jshint -W079 */
var jade = jade || {};
jade.templates = girder.templates;

module.exports = girder;
