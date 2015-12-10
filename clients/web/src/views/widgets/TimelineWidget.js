/**
 * This widget displays a colorful timeline of events.
 */
girder.views.TimelineWidget = girder.View.extend({
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
     * @param [settings.showLabels=false] Whether to show start and end time labels below
     *    the timeline.
     * @param [settings.defaultColor='#aaa'] A CSS color string to use for points
     *    or segments that do not specify a color property.
     * @param [settings.segments=[]] A list of segments. Each element of the list
     *    should be an object with the following keys:
     *      - start: A number or timestamp representing
     *      - end: A numer of timestamp representing the end of this segment.
     *      - [class]: A CSS color string used to color the segment. Uses the
     *                 widget's defaultColor if this key is not set.
     *      - [tooltip]: A tooltip value for this segment. Tooltips containing the
     *                   special token "%r" will have that token expanded into the
     *                   elapsed time between start and end.
     * @param [settings.points=[]] A list of points. Each element of the list should
     *    be an object with the following keys:
     *      - time: A number or timestamp representing the location of the point.
     *      - [class]: A CSS class name to apply to the point.
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
        this.showLabels = !!settings.showLabels;
        this.defaultClass = '';

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
            var classes = segment.class ? [segment.class] : ['g-segment-default'];

            if (segment.tooltip) {
                classes.push('g-tooltip');
            }

            return {
                class: classes.join(' '),
                left: (100 * (start - this.startTime) / range).toFixed(1) + '%',
                width: (100 * (end - start) / range).toFixed(1) + '%',
                tooltip: this._segmentTooltip(segment, {
                    range: this.numeric ? end - start : (end - start) / 1000
                })
            };
        }, this);

        this._processedPoints = _.map(this.points, function (point) {
            var time = this.numeric ? point.time : new Date(point.time);
            var classes = point.class ? [point.class] : ['g-point-default'];

            if (point.tooltip) {
                classes.push('g-tooltip');
            }

            return {
                class: classes.join(' '),
                left: (100 * (time - this.startTime) / range).toFixed(1) + '%',
                tooltip: this._pointTooltip(point, {
                    time: time
                })
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
        this.$el.html(girder.templates.timeline({
            showLabels: this.showLabels,
            defaultColor: this.defaultColor,
            segments: this._processedSegments,
            points: this._processedPoints
        }));

        this.$('.g-tooltip').tooltip({
            delay: 100
        });

        return this;
    }
});
