import _ from 'underscore';
import Backbone from 'backbone';

import events from 'girder/events';
import eventStream from 'girder/utilities/EventStream';

var View = Backbone.View.extend({
    constructor: function (opts) { // eslint-disable-line backbone/no-constructor
        if (opts && _.has(opts, 'parentView')) {
            if (opts.parentView) {
                opts.parentView.registerChildView(this);
                this.parentView = opts.parentView;
            }
        } else {
            console.error('View created with no parentView property set. ' +
                          'This view may not be garbage collected.');
        }
        Backbone.View.prototype.constructor.apply(this, arguments);
    },

    /**
     * Remove a view, unbinding its events and removing its listeners on
     * events so that it can be garbage collected.
     */
    destroy: function () {
        _.each(this._childViews, function (child) {
            child.destroy();
        });
        this._childViews = null;

        this.undelegateEvents();
        this.stopListening();
        this.off();
        events.off(null, null, this);
        eventStream.off(null, null, this);

        if (this.parentView) {
            this.parentView.unregisterChildView(this);
        }

        // Modal views need special cleanup.
        if (this.$el.is('.modal')) {
            var el = this.$el;
            if (el.data('bs.modal') && el.data('bs.modal').isShown) {
                el.on('hidden.bs.modal', function () {
                    el.empty().off().removeData();
                }).modal('hide');
                el.modal('removeBackdrop');
            } else {
                el.modal('hideModal');
                el.modal('removeBackdrop');
                el.empty().off().removeData();
            }
        } else {
            this.$el.empty().off().removeData();
        }
    },

    /**
     * It's typically not necessary to call this directly. Instead, instantiate
     * child views with the "parentView" field.
     */
    registerChildView: function (child) {
        this._childViews = this._childViews || [];
        this._childViews.push(child);
    },

    /**
     * Typically, you will not need to call this method directly. Calling
     * destroy on a child element will automatically unregister it from its
     * parent view if the parent view was specified.
     */
    unregisterChildView: function (child) {
        this._childViews = _.without(this._childViews, child);
    }
});

export default View;

