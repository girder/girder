import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import { getApiRoot, restRequest } from 'girder/rest';

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
        streamPath: '/notification/stream',
        _heartbeatTimeout: 5000 // in milliseconds
    };

    // User-provided settings from initialization
    this.settings = _.extend(defaults, settings);
    // Whether this is opened
    this._opened = false;
    // Whether this is started (if so, holds the EventSource instance)
    this._eventSource = null;
    // The identifier for the next heartbeat check
    this._animationRequestID = null;
    // The identifier for the next dead man's switch check
    this._timeoutID = null;

    return _.extend(this, Backbone.Events);
}

/*
 * This method is used to stop the event stream socket when the Girder tab is not visible.
 *
 * It creates a dead man switch to close the frame after _heartbeatTimeout milliseconds (default of 5 seconds) if
 * requestAnimationFrame is not called in that time.
 */
EventStream.prototype._heartbeat = function () {
    // This has been called because it's the next animation frame or from an explicit startup

    if (!this._opened) {
        // This should never happen
        console.warn('EventStream._heartbeat called on a closed stream.');
        return;
    }

    // If _heartbeat was called from a place other than an animation frame, ensure there are no pending calls queued
    window.cancelAnimationFrame(this._animationRequestID);
    // Schedule the next heartbeat check
    // FIXME: This is a recursive call, which is growing the stack on every animation frame!
    this._animationRequestID = window.requestAnimationFrame(_.bind(this._heartbeat, this));

    // Reset the dead man's switch
    window.clearTimeout(this._timeoutID);
    this._timeoutID = window.setTimeout(() => {
        // If the dead man's switch fires, stop the event stream, but leave it open
        this._stop();
        // Note, there is still a pending heartbeat call whenever the page is rendered next
    }, this.settings._heartbeatTimeout);

    if (!this._eventSource) {
        // EventStream is open but stopped
        this._start();
    }
};

EventStream.prototype.open = function () {
    if (!window.EventSource) {
        console.error('EventSource is not supported on this platform.');
        return;
    }

    this._opened = true;
    this._start();
};

EventStream.prototype._start = function () {
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

    this._eventSource.onmessage = (e) => {
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
    this._eventSource.onerror = () => {
        // The EventSource.onerror API does not provide the HTTP status code of the error, so send an Ajax HEAD request
        // to capture the status code.
        restRequest({
            url: this.settings.streamPath,
            method: 'HEAD',
            error: null
        })
            .fail((jqXHR) => {
                if (jqXHR.status === 503) {
                    // Notification stream is disabled, so close this EventStream
                    this.close();
                }
            });
        // In all other cases (HEAD doesn't fail, or fails with a non-503 code), assume this is a temporary outage and
        // allow the EventStream to continue attempting to auto-connect
    };

    this._heartbeat();
    this.trigger('g:eventStream.start');
};

EventStream.prototype._stop = function () {
    if (this._eventSource) {
        this._eventSource.close();
        this._eventSource = null;
    }
    this.trigger('g:eventStream.stop');
};

EventStream.prototype.close = function () {
    this._opened = false;
    this._stop();
    window.cancelAnimationFrame(this._animationRequestID);
    window.clearTimeout(this._timeoutID);
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
