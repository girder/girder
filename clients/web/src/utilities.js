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
    "use strict";
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
    "use strict";
    if (sizeBytes === 0) {
        return 'no space';
    }

    var units = ['B', 'KB', 'MB', ' GB', 'TB'];
    for (var i = 0; sizeBytes > 1024; i += 1) {
        sizeBytes /= 1024;
    }

    return sizeBytes.toFixed(1) + ' ' + units[i];
};
