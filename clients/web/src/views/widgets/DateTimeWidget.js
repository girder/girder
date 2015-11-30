/* globals moment */

/**
 * This widget provides a text input field to specify a date/time. The user
 * chooses the date/time using a popup picker.
 */
girder.views.DateTimeWidget = girder.View.extend({

    /**
     * @param [settings.prefix='default'] Prefix for element IDs in case
     *     multiple DateTimeWidgets are rendered simultaneously.
     */
    initialize: function (settings) {
        this.prefix = settings.prefix || 'default';
        this.dateTimeId = '#' + this.prefix + '-datetime';
    },

    render: function () {
        this.$el.html(girder.templates.dateTimeWidget({
            prefix: this.prefix
        }));

        this.$(this.dateTimeId).datetimepicker({
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
            }
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
        var picker = this.$(this.dateTimeId).data('DateTimePicker');
        return picker;
    }
});

/**
 * This widget provides text input fields to specify a range of dates/times.
 * That is, the first field specifies "from" and the second field specifies
 * "to." The user chooses each date/time using a popup picker.
 */
girder.views.DateTimeRangeWidget = girder.View.extend({

    /**
     * @param [settings.prefix='default'] Prefix for element IDs in case
     *     multiple DateTimeRangeWidgets are rendered simultaneously.
     */
    initialize: function (settings) {
        this.prefix = settings.prefix || 'default';
        this.dateTimeFromId = '#' + this.prefix + '-datetime-from';
        this.dateTimeToId = '#' + this.prefix + '-datetime-to';
    },

    render: function () {
        var view = this;

        view.$el.html(girder.templates.dateTimeRangeWidget({
            prefix: view.prefix
        }));

        // Link datetimepickers to disallow choosing range where "from" date is
        // after "to" date

        var options = {
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
            }
        };
        view.$(view.dateTimeFromId).datetimepicker(options);

        options['useCurrent'] = false;
        view.$(view.dateTimeToId).datetimepicker(options);

        $(view.dateTimeFromId).on('dp.change', function (e) {
            var picker = view._picker(view.dateTimeToId);
            picker.minDate(e.date);
        });
        $(view.dateTimeToId).on('dp.change', function (e) {
            var picker = view._picker(view.dateTimeFromId);
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
        this._setDate(this.dateTimeFromId, date);
    },

    /**
     * Set "to" date/time. Argument can be an ISO 8601-formatted date string,
     * a moment object, or a Date object. Call with null or the empty string to
     * clear. When called with a string, the widget displays in local time.
     *
     * @param date To date/time to display.
     */
    setToDate: function (date) {
        this._setDate(this.dateTimeToId, date);
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
        return this._date(this.dateTimeFromId);
    },

    /**
     * Get the "to" date/time as a moment object in UTC. Returns null if no date
     * is set.
     */
    toDate: function () {
        return this._date(this.dateTimeToId);
    },

    /**
     * Convenience function to return "from" the date/time as a string in UTC.
     * Returns the empty string if no date is set.
     */
    fromDateString: function () {
        return this._dateString(this.dateTimeFromId);
    },

    /**
     * Convenience function to return the "to" date/time as a string in UTC.
     * Returns the empty string if no date is set.
     */
    toDateString: function () {
        return this._dateString(this.dateTimeToId);
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
