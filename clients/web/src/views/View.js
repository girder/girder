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
    },

    /**
     * Disable Bootstrap tooltips at and below the level of "targetEl".
     */
    _disableBootstrapTooltips: function (targetEl) {
        // While binding to "show.bs.tooltip" and calling "event.preventDefault()" is sufficient to
        // prevent Bootstrap tooltips from actually appearing, the default browser-rendered tooltips
        // will no longer be displayed, due to the fact that Bootstrap still initializes all
        // tooltip-eligible elements as 'Bootstrap tooltips', which has the side effect of renaming
        // the "title" attribute.
        //
        // For dynamically-created elements, this initialization is done
        // during the "hover" and "focus" pseudo-events (which Bootstrap translates to the real
        // "mouseenter", "mouseleave", "focusin", and "focusout" events in the "tooltip" namespace).
        // Blocking these events from reaching Bootstrap is complicated by the fact that
        // "mouseenter" and "mouseleave" don't bubble, so they can't be caught at the "targetEl"
        // and have "stopPropagation()" be called to stop the bubbling up to where the tooltip
        // handler is attached.
        //
        // So, here we add a "[title]" selector, to cause our handler to run when any
        // tooltip-containing element directly receives one of our target event. Despite the fact
        // that some of these events do not technically bubble, both this and the Bootstrap event
        // handlers are delegated, and thus are handled in ascending DOM order from the original
        // target; accordingly our handler (attached to the "targetEl") will be run first, and able
        // to "stopPropagation()" up to the Bootstrap tooltip handler (typically attached to the
        // root element of the App).
        targetEl.on(
            'mouseenter.tooltip mouseleave.tooltip focusin.tooltip focusout.tooltip',
            '[title]',
            (event) => {
                event.stopPropagation();
            });
    }
});

export default View;
