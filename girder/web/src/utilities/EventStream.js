import _ from 'underscore';
import Backbone from 'backbone';

import { getCurrentToken } from '@girder/core/auth';

/**
 * The EventStream is an abstraction for server-sent events / long-polling via a
 * per-user event channel endpoint using a WebSocket. When events are
 * received on the websocket channel, this triggers a Backbone event of the form
 * 'g:event.<type>' where <type> is the value of the event type field.
 * Listeners can bind to specific event types on the channel.
 */
function EventStream(settings) {
    // Possible states are 'closed', 'stopped', 'started'
    this._state = 'closed';

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
        console.error('Invalid JSON from notification stream: ' + e.data + ',' + err);
        this.trigger('g:error', e);
        return;
    }
    this.trigger('g:event.' + obj.type, obj);
};

EventStream.prototype._onError = function () {
    // TODO: Handle error
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

    this._websocket = new WebSocket(`/notifications/me?token=${getCurrentToken()}`);
    this._websocket.onmessage = this._onMessage;
    this._websocket.onerror = this._onError;

    this._state = 'started';
    this.trigger('g:eventStream.start');
};

EventStream.prototype._stop = function () {
    if (this._state !== 'started') {
        console.warn('EventStream should be started');
        return;
    }

    this._websocket.close();
    this._websocket = null;

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

const eventStream = new EventStream();

export default eventStream;
