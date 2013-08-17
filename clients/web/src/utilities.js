/**
 * This file contains utility functions for general use in the application
 */

/**
 * Show a modal dialog with the given options.
 * @param opts Params to pass to the dialog jade template (text, title, dismissText)
 * @param modalOpts Params to pass to the bootstrap modal function
 */
girder.dialog = function (opts, modalOpts) {
    var defaults = {
        title: 'Info',
        dismissText: 'Close'
    };
    $('#g-dialog-container').html(jade.templates.dialog($.extend(defaults, opts)));
    $('#g-modal-dialog').modal($.extend({}, modalOpts));
};
