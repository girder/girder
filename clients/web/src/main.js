import $ from 'jquery';

import App from 'girder/views/App';
import router from 'girder/router';
import events from 'girder/events';

import 'girder/utilities/jquery/girderModal';

import * as girder from 'girder';

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
