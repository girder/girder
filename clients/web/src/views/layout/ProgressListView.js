/**
 * Container showing list of active tasks that are reporting progress
 * via a girder.EventStream object.
 */
girder.views.ProgressListView = Backbone.View.extend({

    initialize: function (settings) {
        this.eventStream = settings.eventStream;
        this.eventStream.on('g:event.progress', this._handleProgress, this);

        // map progress IDs to widgets
        this._map = {};
    },

    render: function () {
        this.$el.html(jade.templates.layoutProgressArea());

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
                progress: progress
            }).render();
        }
        this._onUpdate();
    },

    _onUpdate: function (event) {
        if (_.isEmpty(this._map)) {
            this.$el.hide();
        }
        else {
            this.$el.show();
        }
    }
});
