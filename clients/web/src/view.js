girder.View = Backbone.View.extend({
    /**
     * Remove a view, unbinding its events and removing its listeners on
     * girder.events so that it can be garbage collected.
     */
    destroy: function () {
        _.each(this._childViews, function (child) {
            child.remove();
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
