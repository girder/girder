import _ from 'underscore';

import { confirm } from 'girder/dialog';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

/**
 * Restart the server, wait until it has restarted, then reload the current
 * page.
 */
function restartServer() {
    function waitForServer() {
        restRequest({
            type: 'GET',
            path: 'system/version',
            error: null
        }).done(_.bind(function (resp) {
            if (resp.serverStartDate !== restartServer._lastStartDate) {
                restartServer._reloadWindow();
            } else {
                window.setTimeout(waitForServer, 1000);
            }
        })).error(_.bind(function () {
            window.setTimeout(waitForServer, 1000);
        }));
    }

    restRequest({
        type: 'GET',
        path: 'system/version'
    }).done(_.bind(function (resp) {
        restartServer._lastStartDate = resp.serverStartDate;
        restartServer._callSystemRestart();
        events.trigger('g:alert', {
            icon: 'cw',
            text: 'Restarting server',
            type: 'warning',
            timeout: 60000
        });
        waitForServer();
    }));
}

function restartServerPrompt() {
    confirm({
        text: 'Are you sure you want to restart the server?  This ' +
            'will interrupt all running tasks for all users.',
        yesText: 'Restart',
        confirmCallback: restartServer
    });
}

/* Having these as object properties facilitates testing */
restartServer._callSystemRestart = function () {
    restRequest({type: 'PUT', path: 'system/restart'});
};

restartServer._reloadWindow = function () {
    window.location.reload();
};

export {
    restartServer,
    restartServerPrompt
};
