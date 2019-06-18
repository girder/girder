import _ from 'underscore';

import View from '@girder/core/views/View';

import TimelineTemplate from '@girder/core/templates/widgets/timeline.pug';

import '@girder/core/stylesheets/widgets/timelineWidget.styl';

/**
 * This widget displays a timeline of events. This is visualized as a line (a bar)
 * with two sorts of primitives overlaid:
 *
 * 1. Segments: spans of time, with a start and end.
 * 2. Points: a single point in time. Points always display on top of segments.
 *
 * Any number of these primitives can be displayed on the timeline, so long as they
 * are bounded between the specified startTime and endTime. The time values for
 * startTime, endTime, and for the primitives can be specified either as numeric
 * values (i.e. a relative offset in time), or as date strings that can be parsed
 * by JavaScript, or as Date objects. For obvious reasons, in a single instance of
 * this widget, it is not possible to mix the numeric/relative values with datestamp
 * values.
 */
var TimelineWidget = View.extend({
    /**
     * Initialize the timeline widget.
     *
     * @param settings.startTime The numeric value or timestamp representing where
     *    the timeline should start.
     * @param settings.endTime The numeric value or timestamp representing where
     *    the timeline should end. Must be greater than the startTime value. All
     *    segments and points should be bounded within the interval [startTime, endTime].
     * @param [settings.numeric=false] If the time values being passed in are simply
     *    relative, scalar values (e.g. number of seconds since start) rather than
     *    timestamps, set this to true.
     * @param [settings.startLabel] Pass to show a label for the start of the timeline.
     * @param [settings.endLabel] Pass to show a label for the end of the timeline.
     * @param [settings.defaultSegmentClass='g-segment-default'] A CSS class set
     *     on segments that do not specify a class.
     * @param [settings.defaultPointClass='g-point-default'] A CSS class set
     *     on points that do not specify a class.
     * @param [settings.segments=[]] A list of segments. Each element of the list
     *    should be an object with the following keys:
     *      - start: A number or timestamp representing
     *      - end: A numer of timestamp representing the end of this segment.
     *      - [class]: A CSS class name to apply to the segment. Uses the
     *                 widget's defaultSegmentClass if this key is not set.
     *      - [tooltip]: A tooltip value for this segment. Tooltips containing the
     *                   special token "%r" will have that token expanded into the
     *                   elapsed time between start and end.
     * @param [settings.points=[]] A list of points. Each element of the list should
     *    be an object with the following keys:
     *      - time: A number or timestamp representing the location of the point.
     *      - [class]: A CSS class name to apply to the point. Uses the
     *                 widget's defaultPointClass if this key is not set.
     *      - [tooltip]: A tooltip value for this point. Tooltips containing the
     *                   special token "%t" will have that token expanded into the
     *                   time value for that point.
     */
    initialize: function (settings) {
        this.startTime = settings.startTime;
        this.endTime = settings.endTime;
        this.segments = settings.segments || [];
        this.points = settings.points || [];
        this.numeric = !!settings.numeric;
        this.startLabel = settings.startLabel;
        this.endLabel = settings.endLabel;
        this.defaultSegmentClass = settings.defaultSegmentClass || 'g-segment-default';
        this.defaultPointClass = settings.defaultPointClass || 'g-point-default';

        this._processData();
    },

    // Processes the points and segments for display in the widget
    _processData: function () {
        if (!this.numeric) {
            this.startTime = new Date(this.startTime);
            this.endTime = new Date(this.endTime);
        }

        if (this.endTime <= this.startTime) {
            console.error('Timeline widget: end time must be after start time.');
            this._processedSegments = [];
            this._processedPoints = [];
            return;
        }

        var range = this.endTime - this.startTime;

        this._processedSegments = _.map(this.segments, function (segment) {
            var start = this.numeric ? segment.start : new Date(segment.start);
            var end = this.numeric ? segment.end : new Date(segment.end);
            var classes = segment.class ? [segment.class] : [this.defaultSegmentClass];
            var color = segment.color ? `background-color: ${segment.color}` : '';

            return {
                class: classes.join(' '),
                left: (100 * (start - this.startTime) / range).toFixed(1) + '%',
                width: (100 * (end - start) / range).toFixed(1) + '%',
                tooltip: this._segmentTooltip(segment, {
                    range: this.numeric ? end - start : (end - start) / 1000
                }),
                color
            };
        }, this);

        this._processedPoints = _.map(this.points, function (point) {
            var time = this.numeric ? point.time : new Date(point.time);
            var classes = point.class ? [point.class] : [this.defaultPointClass];
            var color = point.color ? `background-color: ${point.color}` : '';

            return {
                class: classes.join(' '),
                left: (100 * (time - this.startTime) / range).toFixed(1) + '%',
                tooltip: this._pointTooltip(point, {
                    time: time
                }),
                color
            };
        }, this);
    },

    _segmentTooltip: function (segment, info) {
        if (!segment.tooltip) {
            return null;
        }

        return segment.tooltip.replace('%r', info.range);
    },

    _pointTooltip: function (point, info) {
        if (!point.tooltip) {
            return null;
        }

        if (this.numeric) {
            return point.tooltip.replace('%t', info.time);
        } else {
            return point.tooltip.replace('%t', info.time.toISOString());
        }
    },

    render: function () {
        this.$el.html(TimelineTemplate({
            segments: this._processedSegments,
            points: this._processedPoints,
            startLabel: this.startLabel,
            endLabel: this.endLabel
        }));

        return this;
    }
});

export default TimelineWidget;
