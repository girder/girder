import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import moment from 'moment';
import * as girder from '@girder/core';

window.girder = girder;

// Some cross-browser globals
if (!window.console) {
    window.console = {
        log: $.noop,
        error: $.noop
    };
}

// For testing and convenience, available now because of testUtils.js reliance on $
window.$ = $;
window._ = _;
window.moment = moment;
window.Backbone = Backbone;
