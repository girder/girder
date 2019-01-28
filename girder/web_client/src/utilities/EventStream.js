import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import { getApiRoot, restRequest } from '@girder/core/rest';

/**
 * The EventStream type wraps window.EventSource to listen to the unified
 * per-user event channel endpoint using the SSE protocol. When events are
 * received on the SSE channel, this triggers a Backbone event of the form
 * 'g:event.<type>' where <type> is the value of the event type field.
 * Listeners can bind to specific event types on the channel.
 */
function EventStream(settings) {
    const defaults = {
        timeout: null,
        streamPath: '/notification/stream'
    };

    // User-provided settings from initialization
    this.settings = _.extend(defaults, settings);
    // Possible states are 'closed', 'stopped', 'started'
    this._state = 'closed';
    // Whether this is started (if so, holds the EventSource instance)
    this._eventSource = null;

    // Create context bindings only once, so they can be referenced when unbinding events
    this._onVisibilityStateChange = _.bind(this._onVisibilityStateChange, this);
    this._onMessage = _.bind(this._onMessage, this);
    this._onError = _.bind(this._onError, this);

    return _.extend(this, Backbone.Events);
}

EventStream.prototype._onVisibilityStateChange = function () {
    if (document.visibilityState === 'visible' && this._state === 'stopped') {
        this._start();
    } else if (document.visibilityState === 'hidden' && this._state === 'started') {
        this._stop();
    }
};

EventStream.prototype._onMessage = function (e) {
    let obj;
    try {
        obj = window.JSON.parse(e.data);
    } catch (err) {
        console.error('Invalid JSON from SSE stream: ' + e.data + ',' + err);
        this.trigger('g:error', e);
        return;
    }
    EventStream.setLastTimestamp(obj._girderTime);
    this.trigger('g:event.' + obj.type, obj);
};

EventStream.prototype._onError = function () {
    // The EventSource.onerror API does not provide the HTTP status code of the error, so send an Ajax HEAD request to
    // capture the status code.
    restRequest({
        url: this.settings.streamPath,
        method: 'HEAD',
        error: null
    })
        .fail((jqXHR) => {
            if (jqXHR.status === 503) {
                // Notification stream is disabled, so close this EventStream
                this.trigger('g:eventStream.disable', jqXHR);
                this.close();
            }
        });
    // In all other cases (HEAD doesn't fail, or fails with a non-503 code), assume this is a temporary outage and allow
    // the EventStream to continue attempting to auto-connect
};

EventStream.prototype.open = function () {
    if (!window.EventSource) {
        console.error('EventSource is not supported on this platform.');
        this.trigger('g:eventStream.disable');
        return;
    }
    if (this._state !== 'closed') {
        console.warn('EventStream should be closed.');
        return;
    }

    this._state = 'stopped';
    this._start();

    document.addEventListener('visibilitychange', this._onVisibilityStateChange);
};

EventStream.prototype._start = function () {
    if (this._state !== 'stopped') {
        console.warn('EventStream should be stopped');
        return;
    }

    const params = {};

    if (this.settings.timeout) {
        params.timeout = this.settings.timeout;
    }

    // Set the "since" argument to filter out notifications that have already been sent to this client.
    const timestamp = EventStream.getLastTimestamp();
    if (_.isNumber(timestamp)) {
        params.since = timestamp;
    }

    const url = getApiRoot() + this.settings.streamPath + '?' + $.param(params);

    this._eventSource = new window.EventSource(url);
    this._eventSource.onmessage = this._onMessage;
    this._eventSource.onerror = this._onError;

    this._state = 'started';
    this.trigger('g:eventStream.start');
};

EventStream.prototype._stop = function () {
    if (this._state !== 'started') {
        console.warn('EventStream should be started');
        return;
    }

    this._eventSource.close();
    this._eventSource = null;

    this._state = 'stopped';
    this.trigger('g:eventStream.stop');
};

EventStream.prototype.close = function () {
    if (this._state === 'closed') {
        console.warn('EventStream should not be closed');
        return;
    }

    document.removeEventListener('visibilitychange', this._onVisibilityStateChange);

    if (this._state === 'started') {
        this._stop();
    }

    this._state = 'closed';
    this.trigger('g:eventStream.close');
};

// Static methods
EventStream._lastTimestamp = null;
EventStream.setLastTimestamp = function (timestamp) {
    try {
        window.localStorage.setItem('sseTimestamp', timestamp);
    } catch (e) {
        // Ignore any errors raised by localStorage
    }
    EventStream._lastTimestamp = timestamp;
};
EventStream.getLastTimestamp = function () {
    let timestamp;
    try {
        timestamp = parseInt(window.localStorage.getItem('sseTimestamp'), 10);
    } catch (e) {
        // Ignore any errors raised by localStorage
    }
    if (!_.isNaN(timestamp)) {
        // An int was parsed
        return timestamp;
    } else {
        // Value could not be gotten from localStorage, so return from fallback (which is also the default of null)f
        return EventStream._lastTimestamp;
    }
};

const eventStream = new EventStream();

export default eventStream;
