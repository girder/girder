girder.View = Backbone.View.extend({
    constructor: function (opts) {
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
     * girder.events so that it can be garbage collected.
     */
    destroy: function () {
        _.each(this._childViews, function (child) {
            child.destroy();
        });
        this._childViews = null;

        this.undelegateEvents();
        this.stopListening();
        this.off();
        girder.events.off(null, null, this);

        if (this.parentView) {
            this.parentView.unregisterChildView(this);
        }

        // If there is an active modal, we need to properly hide it, then destroy
        if (this.$el.is('.modal.in')) {
            var el = this.$el;
            el.on('hidden.bs.modal', function () {
                el.off().removeData().empty();
            }).modal('hide');
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
