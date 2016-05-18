var $                  = require('jquery');
var _                  = require('underscore');
var View               = require('girder/view');
var TaskProgressWidget = require('girder/views/widgets/TaskProgressWidget');

var LayoutProgressAreaTemplate = require('girder/templates/layout/layoutProgressArea.jade');

/**
 * Container showing list of active tasks that are reporting progress
 * via a EventStream object.
 */
var ProgressListView = View.extend({

    initialize: function (settings) {
        this.eventStream = settings.eventStream;
        this.eventStream.on('g:event.progress', this._handleProgress, this);

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
            var el = $('<div/>', {
                class: 'g-progress-widget-container'
            }).appendTo(this.$('.g-progress-list-container'));

            this._map[progress._id] = new TaskProgressWidget({
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

    _onUpdate: function () {
        if (_.isEmpty(this._map)) {
            this.$el.hide();
        } else {
            this.$el.show();
        }
    }
});

module.exports = ProgressListView;
