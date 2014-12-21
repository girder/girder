girder.View = Backbone.View.extend({
    constructor: function (opts) {
        if (opts && _.has(opts, 'parentView')) {
            if (opts.parentView) {
                opts.parentView.registerChildView(this);
            }
        } else {
            console.error('View created with no parentView property set. ' +
                          'This view may not be garbage collected.')
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
     * Views should register their child views using this function so that they
     * can be cleaned up when the parent is destroyed.
     */
    registerChildView: function (child) {
        this._childViews = this._childViews || [];
        this._childViews.push(child);
    }
});
