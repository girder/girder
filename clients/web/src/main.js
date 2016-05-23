import $      from 'jquery';

import App    from 'girder/app';
import Events from 'girder/events';
import router from 'girder/router';

import 'girder/utilities/jQuery'; // $.girderModal

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

    Events.trigger('g:appload.before');
    var mainApp = new App({
        el: 'body',
        parentView: null
    });
    Events.trigger('g:appload.after', mainApp);
});
