import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';
import moment from 'moment';

import App from 'girder/views/App';
import router from 'girder/router';
import { events } from 'girder/events';

import 'girder/utilities/jquery/girderModal';

import * as girder from 'girder';

// Some cross-browser globals
if (!window.console) {
    window.console = {
        log: $.noop,
        error: $.noop
    };
}

// When all scripts are loaded, we invoke the application
$(function () {
    // When the back button is pressed, we want to close open modals.
    router.on('route', function (route, params) {
        if (!params.slice(-1)[0].dialog) {
            $('.modal').girderModal('close');
        }
        // get rid of tooltips
        $('.tooltip').remove();
    });

    events.trigger('g:appload.before');
    var mainApp = new App({
        el: 'body',
        parentView: null
    });
    events.trigger('g:appload.after', mainApp);

    // Available only after all code+plugins have been loaded, to make sure they don't
    // rely on the singleton. Tests should be abe to use it though.
    window.girder = girder;
});

// For testing and convenience, available now because of testUtils.js reliance on $
window.$ = $;
window._ = _;
window.moment = moment;
window.Backbone = Backbone;
