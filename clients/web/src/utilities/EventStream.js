import _ from 'underscore';
import Backbone from 'backbone';

import { apiRoot } from 'girder/rest';

/**
 * The EventStream type wraps window.EventSource to listen to the unified
 * per-user event channel endpoint using the SSE protocol. When events are
 * received on the SSE channel, this triggers a Backbone event of the form
 * 'g:event.<type>' where <type> is the value of the event type field.
 * Listeners can bind to specific event types on the channel.
 */
function EventStream(settings) {
    var defaults = {
        timeout: null,
        streamPath: '/notification/stream'
    };

    this.settings = _.extend(defaults, settings);

    return _.extend(this, Backbone.Events);
}

var prototype = EventStream.prototype;

prototype.open = function () {
    if (window.EventSource) {
        var stream = this,
            url = apiRoot + this.settings.streamPath;

        if (this.settings.timeout) {
            url += '?timeout=' + this.settings.timeout;
        }

        this._eventSource = new window.EventSource(url);

        this._eventSource.onmessage = function (e) {
            var obj;
            try {
                obj = window.JSON.parse(e.data);
            } catch (err) {
                console.error('Invalid JSON from SSE stream: ' + e.data + ',' + err);
                stream.trigger('g:error', e);
                return;
            }
            stream.trigger('g:event.' + obj.type, obj);
        };
    } else {
        console.error('EventSource is not supported on this platform.');
    }
};

prototype.close = function () {
    if (this._eventSource) {
        this._eventSource.close();
        this._eventSource = null;
    }
};

var eventStream = new EventStream();

export default eventStream;
