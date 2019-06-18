import _ from 'underscore';
import moment from 'moment';

import View from '@girder/core/views/View';

import dateTimeRangeWidgetTemplate from '@girder/core/templates/widgets/dateTimeRangeWidget.pug';

import 'eonasdan-bootstrap-datetimepicker'; // /src/js/bootstrap-datetimepicker.js'
import 'eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.css';

/**
 * This widget provides text input fields to specify a range of dates/times.
 * That is, the first field specifies "from" and the second field specifies
 * "to." The user chooses each date/time using a popup picker.
 */
var DateTimeRangeWidget = View.extend({

    /**
     * @param [settings.defaultFromDate=false] The default "from" date/time when
     * not set explicitly. Set to false to have no default.
     * @param [settings.defaultToDate=false] The default "to" date/time when not
     * set explicitly. Set to false to have no default.
     * @param [settings.showIcon=true] Whether to show calendar icons beside
     * the input fields. When true, clicking the icon shows the popup. Otherwise,
     * focusing the input field shows the popup.
     * @param [settings.fromLabel='Start date'] The label text for the "from"
     * input field.
     * @param [settings.toLabel='End date'] The label text for the "to" input
     * field.
     */
    initialize: function (settings) {
        this.defaultFromDate = settings.defaultFromDate || false;
        this.defaultToDate = settings.defaultToDate || false;
        this.showIcon = _.has(settings, 'showIcon') ? settings.showIcon : true;
        this.fromLabel = settings.fromLabel || 'Start date';
        this.toLabel = settings.toLabel || 'End date';
    },

    render: function () {
        this.$el.html(dateTimeRangeWidgetTemplate({
            showIcon: this.showIcon,
            fromLabel: this.fromLabel,
            toLabel: this.toLabel
        }));

        // Link datetimepickers to disallow choosing range where "from" date is
        // after "to" date

        var options = {
            showClear: true,
            showTodayButton: true,
            icons: {
                time: 'icon-clock',
                date: 'icon-calendar',
                up: 'icon-up-open',
                down: 'icon-down-open',
                previous: 'icon-left-open',
                next: 'icon-right-open',
                clear: 'icon-trash',
                close: 'icon-cancel',
                today: 'icon-target'
            }
        };
        options.useCurrent = 'day';
        options.defaultDate = this.defaultFromDate;
        this.$('.g-datetime-widget-from').datetimepicker(options);

        options.useCurrent = false;
        options.defaultDate = this.defaultToDate;
        this.$('.g-datetime-widget-to').datetimepicker(options);

        this.$('.g-datetime-widget-from').on('dp.change', (e) => {
            var picker = this._picker('.g-datetime-widget-to');
            picker.minDate(e.date);
        });
        this.$('.g-datetime-widget-to').on('dp.change', (e) => {
            var picker = this._picker('.g-datetime-widget-from');
            picker.maxDate(e.date);
        });

        return this;
    },

    /**
     * Set "from" date/time. Argument can be an ISO 8601-formatted date string,
     * a moment object, or a Date object. Call with null or the empty string to
     * clear. When called with a string, the widget displays in local time.
     *
     * @param date From date/time to display.
     */
    setFromDate: function (date) {
        this._setDate('.g-datetime-widget-from', date);
    },

    /**
     * Set "to" date/time. Argument can be an ISO 8601-formatted date string,
     * a moment object, or a Date object. Call with null or the empty string to
     * clear. When called with a string, the widget displays in local time.
     *
     * @param date To date/time to display.
     */
    setToDate: function (date) {
        this._setDate('.g-datetime-widget-to', date);
    },

    /*
     * Convenience function to set date/time for a specified datetimepicker.
     *
     * @param [id] Element ID on which to access the datetimepicker.
     */
    _setDate: function (id, date) {
        var picker = this._picker(id);
        if (_.isEmpty(date)) {
            picker.clear();
        } else if (_.isString(date)) {
            var localDate = moment.utc(date).local();
            picker.date(localDate);
        } else {
            picker.date(date);
        }
    },

    /**
     * Get the "from" date/time as a moment object in UTC. Returns null if no
     * date is set.
     */
    fromDate: function () {
        return this._date('.g-datetime-widget-from');
    },

    /**
     * Get the "to" date/time as a moment object in UTC. Returns null if no date
     * is set.
     */
    toDate: function () {
        return this._date('.g-datetime-widget-to');
    },

    /**
     * Convenience function to return "from" the date/time as a string in UTC.
     * Returns the empty string if no date is set.
     */
    fromDateString: function () {
        return this._dateString('.g-datetime-widget-from');
    },

    /**
     * Convenience function to return the "to" date/time as a string in UTC.
     * Returns the empty string if no date is set.
     */
    toDateString: function () {
        return this._dateString('.g-datetime-widget-to');
    },

    _picker: function (id) {
        var picker = this.$(id).data('DateTimePicker');
        return picker;
    },

    _date: function (id) {
        var picker = this._picker(id);
        var date = picker.date();
        if (date !== null) {
            date = moment(date);
            date.utc();
        }
        return date;
    },

    _dateString: function (id) {
        var date = this._date(id);
        if (date === null) {
            return '';
        }
        return date.format();
    }
});

export default DateTimeRangeWidget;
