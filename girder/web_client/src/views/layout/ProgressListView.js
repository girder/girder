import _ from 'underscore';

import TaskProgressWidget from '@girder/core/views/widgets/TaskProgressWidget';
import View from '@girder/core/views/View';

import LayoutProgressAreaTemplate from '@girder/core/templates/layout/layoutProgressArea.pug';

import '@girder/core/stylesheets/layout/progressArea.styl';

/**
 * Container showing list of active tasks that are reporting progress
 * via a EventStream object.
 */
var ProgressListView = View.extend({

    initialize: function (settings) {
        this.eventStream = settings.eventStream;
        this.listenTo(this.eventStream, 'g:event.progress', this._handleProgress, this);
        // if the event stream disconnects, clear the progress so we don't have
        // stale values lingering.
        this.listenTo(this.eventStream, 'g:eventStream.stop', this._clearProgress, this);

        // map progress IDs to widgets
        this._map = {};
    },

    render: function () {
        this.$el.html(LayoutProgressAreaTemplate());

        this._onUpdate();

        return this;
    },

    _handleProgress: function (progress) {
        if (_.has(this._map, progress._id)) {
            this._map[progress._id].update(progress);
        } else {
            this._map[progress._id] = new TaskProgressWidget({
                className: 'g-progress-widget-container',
                progress: progress,
                parentView: null
            }).on('g:hide', function (p) {
                this._map[p._id].destroy();
                delete this._map[p._id];
                this._onUpdate();
            }, this).render();
            this._map[progress._id].$el.appendTo(this.$('.g-progress-list-container'));
        }
        this._onUpdate();
    },

    _clearProgress: function () {
        const needsUpdate = !_.isEmpty(this._map);
        _.each(this._map, (progressWidget, progressId) => {
            progressWidget.destroy();
            progressWidget.remove();
            delete this._map[progressId];
        });
        if (needsUpdate) {
            this._onUpdate();
        }
    },

    _onUpdate: function () {
        this.$el.toggle(!_.isEmpty(this._map));
    }
});

export default ProgressListView;
