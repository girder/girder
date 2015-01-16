/**
 * Container showing list of active tasks that are reporting progress
 * via a girder.EventStream object.
 */
girder.views.ProgressListView = girder.View.extend({

    initialize: function (settings) {
        this.eventStream = settings.eventStream;
        this.eventStream.on('g:event.progress', this._handleProgress, this);

        // map progress IDs to widgets
        this._map = {};
    },

    render: function () {
        this.$el.html(girder.templates.layoutProgressArea());

        this._onUpdate();

        return this;
    },

    _handleProgress: function (progress) {
        if (_.has(this._map, progress._id)) {
            this._map[progress._id].update(progress);
        } else {
            var el = $('<div/>', {
                class: 'g-progress-widget-container'
            }).appendTo(this.$('.g-progress-list-container'));

            this._map[progress._id] = new girder.views.TaskProgressWidget({
                el: el,
                progress: progress,
                parentView: null
            }).on('g:hide', function (p) {
                this._map[p._id].destroy();
                delete this._map[p._id];
                this._onUpdate();
            }, this).render();
        }
        this._onUpdate();
    },

    _onUpdate: function (event) {
        if (_.isEmpty(this._map)) {
            this.$el.hide();
        } else {
            this.$el.show();
        }
    }
});
