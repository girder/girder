girder.View = Backbone.View.extend({
    constructor: function (opts) {
        if (opts && _.has(opts, 'parentView')) {
            if (opts.parentView) {
                opts.parentView.registerChildView(this);
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
        this.$el.empty();
    },

    /**
     * It's typically not necessary to call this directly; instead, instantiate
     * child views with the "parentView" field.
     */
    registerChildView: function (child) {
        this._childViews = this._childViews || [];
        this._childViews.push(child);
    },

    /**
     * Use this if you manually destroy a child view and need to remove it from
     * the child list.
     */
    unregisterChildView: function (child) {
        this._childViews = _.without(this._childViews, child);
    }
});
