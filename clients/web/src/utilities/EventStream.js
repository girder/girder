(function () {
    /**
     * The EventStream type wraps window.EventSource to listen to the unified
     * per-user event channel endpoint using the SSE protocol. When events are
     * received on the SSE channel, this triggers a Backbone event of the form
     * 'g:event.<type>' where <type> is the value of the event type field.
     * Listeners can bind to specific event types on the channel.
     */
    girder.EventStream = function () {
        return _.extend(this, Backbone.Events);
    };

    var prototype = girder.EventStream.prototype;

    prototype.open = function () {
        if (window.EventSource) {
            this._eventSource = new window.EventSource(
                girder.apiRoot + '/notification/stream?token=' +
                girder.cookie.find('girderToken'));

            var stream = this;

            this._eventSource.onmessage = function (e) {
                try {
                    var obj = window.JSON.parse(e.data);
                    stream.trigger('g:event.' + obj.type, obj);
                } catch (err) {
                    console.error('Invalid JSON from SSE stream: ' + e.data + ',' + err);
                    stream.trigger('g:error', e);
                }
            };
        } else {
            console.error('EventSource is not supported on this platform.');
        }
    };

    prototype.close = function () {
        if (this._eventSource) {
            this._eventSource.close();
        }
    };
} ());
