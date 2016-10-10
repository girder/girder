import _ from 'underscore';
import moment from 'moment';

import View from 'girder/views/View';

import dateTimeWidgetTemplate from 'girder/templates/widgets/dateTimeWidget.pug';

import 'eonasdan-bootstrap-datetimepicker'; // /src/js/bootstrap-datetimepicker.js'
import 'eonasdan-bootstrap-datetimepicker/build/css/bootstrap-datetimepicker.css';

/**
 * This widget provides a text input field to specify a date/time. The user
 * chooses the date/time using a popup picker.
 */
var DateTimeWidget = View.extend({

    /**
     * @param [settings.defaultDate=false] The default date/time when not set
     * explicitly. Set to false to have no default.
     * @param [settings.showIcon=true] Whether to show a calendar icon beside
     * the input field. When true, clicking the icon shows the popup. Otherwise,
     * focusing the input field shows the popup.
     */
    initialize: function (settings) {
        this.defaultDate = settings.defaultDate || false;
        this.showIcon = _.has(settings, 'showIcon') ? settings.showIcon : true;
    },

    render: function () {
        this.$el.html(dateTimeWidgetTemplate({
            showIcon: this.showIcon
        }));

        this.$('.g-datetime-widget').datetimepicker({
            showClear: true,
            showTodayButton: true,
            useCurrent: 'day',
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
            },
            defaultDate: this.defaultDate
        });

        return this;
    },

    /**
     * Set date/time. Argument can be an ISO 8601-formatted date string, a
     * moment object, or a Date object. Call with null or the empty string to
     * clear. When called with a string, the widget displays in local time.
     *
     * @param date Date/time to display.
     */
    setDate: function (date) {
        var picker = this._picker();
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
     * Get the date/time as a moment object in UTC. Returns null if no date is
     * set.
     */
    date: function () {
        var picker = this._picker();
        var date = picker.date();
        if (date !== null) {
            date = moment(date);
            date.utc();
        }
        return date;
    },

    /**
     * Convenience function to return the date/time as a string in UTC. Returns
     * the empty string if no date is set.
     */
    dateString: function () {
        var date = this.date();
        if (date === null) {
            return '';
        }
        return date.format();
    },

    /**
     * Convenience function to access the datetimepicker on an element.
     */
    _picker: function () {
        var picker = this.$('.g-datetime-widget').data('DateTimePicker');
        return picker;
    }
});

export default DateTimeWidget;

