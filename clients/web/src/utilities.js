/**
 * This file contains utility functions for general use in the application
 */
girder.DATE_MONTH = 0;
girder.DATE_DAY = 1;
girder.DATE_MINUTE = 2;
girder.DATE_SECOND = 3;

/**
 * Format a date string to the given resolution.
 * @param datestr The date string to format.
 * @param resolution The resolution, defaults to 'day'. Minimum is month.
 */
girder.formatDate = function (datestr, resolution) {
    var date = new Date(datestr);
    var output = girder.MONTHS[date.getMonth()];

    resolution = resolution || girder.DATE_MONTH;

    if (resolution >= girder.DATE_DAY) {
        output += ' ' + date.getDate() + ',';
    }

    output += ' ' + date.getFullYear();

    if (resolution >= girder.DATE_MINUTE) {
        output += date.getHours() + ':' + date.getMinutes();
    }
    if (resolution >= girder.DATE_SECOND) {
        output += ':' + date.getSeconds();
    }

    return output;
};

/**
 * Format a size in bytes into a human-readable string with metric unit prefixes.
 */
girder.formatSize = function (sizeBytes) {
    if (sizeBytes === 0) {
        return 'no space';
    }

    var units = ['B', 'KB', 'MB', 'GB', 'TB'];
    for (var i = 0; sizeBytes > 1024; i += 1) {
        sizeBytes /= 1024;
    }

    return sizeBytes.toFixed(1) + ' ' + units[i];
};

/**
 * Prompt the user to confirm an action.
 * @param [text] The text to prompt the user with.
 * @param [yesText] The text for the confirm button.
 * @param [yesClass] Class string to apply to the confirm button.
 * @param [noText] The text for the no/cancel button.
 * @param confirmCallback Callback function when the user confirms the action.
 */
girder.confirm = function (params) {
    params = _.extend({
        text: 'Are you sure?',
        yesText: 'Yes',
        yesClass: 'btn-danger',
        noText: 'Cancel'
    }, params);
    $('#g-dialog-container').html(jade.templates.confirmDialog({
        params: params
    })).modal();

    $('#g-dialog-container').find('.modal-body>p').html(params.text);

    $('#g-confirm-button').unbind('click').click(function () {
        $('#g-dialog-container').modal('hide');
        params.confirmCallback();
    });
};
