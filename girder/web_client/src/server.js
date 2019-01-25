import $ from 'jquery';

import { confirm } from '@girder/core/dialog';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';

/**
 * Periodically re-run a promise-returning function, until it is fulfilled.
 * @param func A promise-returning function, taking no arguments.
 * @param delay A delay, in milliseconds, to wait before re-running a rejected "func".
 * @returns {$.Promise} A promise, which fulfills with the same values as the fulfilled "func".
 */
function _retryUntilFulfilled(func, delay) {
    const resolution = $.Deferred();
    const loop = () => {
        // Run the function
        func()
            .done(function () {
                // If it's fulfilled, then fulfill the resolution with the same values
                resolution.resolve.apply(resolution, arguments);
            })
            .fail(() => {
                // If it's rejected, check again
                window.setTimeout(loop, delay);
            });
    };
    loop();
    return resolution.promise();
}

/**
 * Restart the server, wait until it has restarted, then reload the current page.
 * @returns {$.Promise} A promise which resolves when the server is restarted.
 */
function restartServer() {
    // Query the server first
    return restRequest({
        method: 'GET',
        url: 'system/version'
    })
        // Restart the server
        .then((resp) => {
            // Store the last start date in an attribute, so testing code can mutate it
            restartServer._lastStartDate = resp.serverStartDate;
            events.trigger('g:alert', {
                icon: 'cw',
                text: 'Restarting server',
                type: 'warning',
                timeout: 60000
            });
            return restartServer._callSystemRestart();
        })
        // Check until the server is restarted
        .then(() => _retryUntilFulfilled(
            () => restartServer._checkServer(restartServer._lastStartDate),
            1000
        ))
        // Reload the window after everything completes
        .done(() => {
            restartServer._reloadWindow();
        });
}

/**
 * Check once whether the server is restarted, returning a promise which reflects the status.
 * @param {string} lastStartDate A timestamp string with the original start date.
 * @returns {$.Promise} A promise which resolves or rejects, depending on the restarted state.
 */
restartServer._checkServer = function (lastStartDate) {
    return restRequest({
        method: 'GET',
        url: 'system/version',
        error: null
    })
        .then((resp) => {
            if (resp.serverStartDate !== lastStartDate) {
                return undefined;
            } else {
                throw undefined;
            }
        });
};

/* Having these as object properties facilitates testing */
restartServer._callSystemRestart = function () {
    return restRequest({
        method: 'PUT',
        url: 'system/restart'
    });
};

restartServer._reloadWindow = function () {
    window.location.reload();
};

function restartServerPrompt() {
    confirm({
        text: 'Are you sure you want to restart the server?  This ' +
            'will interrupt all running tasks for all users.',
        yesText: 'Restart',
        confirmCallback: restartServer
    });
}

export {
    restartServer,
    restartServerPrompt
};
