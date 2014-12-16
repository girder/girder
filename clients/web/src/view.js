girder.View = Backbone.View.extend({
    /**
     * Views should register their child girder.View objects so that they can
     * be automatically destroyed when the parent is destroyed.
     */
    childViews: [],

    /**
     * Remove a view, unbinding its events and removing its listeners on
     * girder.events so that it can be garbage collected.
     */
    destroy: function () {
        this.$el.empty();
        this.undelegateEvents();
        this.off();
        girder.events.off(null, null, this);

        _.each(this.childViews, function (child) {
            child.destroy();
        });
    }
});
