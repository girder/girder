import { confirm } from 'girder/dialog';
import events from 'girder/events';
import { restRequest } from 'girder/rest';

/**
 * Restart the server, wait until it has restarted, then reload the current
 * page.
 */
function restartServer() {
    function waitForServer() {
        return new Promise((resolve, reject) => {
            function wait() {
                restRequest({
                    type: 'GET',
                    path: 'system/version',
                    error: null
                }).done(resp => {
                    if (resp.serverStartDate !== restartServer._lastStartDate) {
                        resolve();
                        restartServer._reloadWindow();
                    } else {
                        window.setTimeout(wait, 1000);
                    }
                }).error(() => {
                    window.setTimeout(wait, 1000);
                });
            }
            wait();
        });
    }

    return Promise.resolve(restRequest({
        type: 'GET',
        path: 'system/version'
    }).done(resp => {
        restartServer._lastStartDate = resp.serverStartDate;
        restartServer._callSystemRestart();
        events.trigger('g:alert', {
            icon: 'cw',
            text: 'Restarting server',
            type: 'warning',
            timeout: 60000
        });
        return waitForServer();
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

function rebuildWebClient() {
    return restartServer._rebuildWebClient();
}

/* Having these as object properties facilitates testing */
restartServer._callSystemRestart = function () {
    restRequest({type: 'PUT', path: 'system/restart'});
};

restartServer._reloadWindow = function () {
    window.location.reload();
};

restartServer._rebuildWebClient = function () {
    return Promise.resolve(restRequest({ path: 'system/web_build', type: 'POST', data: { progress: true } }));
};

export {
    restartServer,
    restartServerPrompt,
    rebuildWebClient
};
