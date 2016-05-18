var $      = require('jquery');
var girder = require('girder/init');
var Events = require('girder/events');
var App    = require('girder/app');
var Router = require('girder/router');

require('girder/utilities/jQuery'); // $.girderModal

// When all scripts are loaded, we invoke the application
$(function () {
    girder.router = new Router();

    // When the back button is pressed, we want to close open modals.
    girder.router.on('route', function (route, params) {
        if (!params.slice(-1)[0].dialog) {
            $('.modal').girderModal('close');
        }
        // get rid of tooltips
        $('.tooltip').remove();
    });

    Events.trigger('g:appload.before');
    girder.mainApp = new App({
        el: 'body',
        parentView: null
    });
    Events.trigger('g:appload.after', girder.mainApp);
});
