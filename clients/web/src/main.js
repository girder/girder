// When all scripts are loaded, we invoke the application
$(function () {
    girder.events.trigger('g:appload.before');
    girder.mainApp = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after', girder.mainApp);
});
