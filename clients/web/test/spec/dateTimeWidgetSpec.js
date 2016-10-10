describe('Test DateTimeWidget', function() {
    var widget;

    describe('default construction', function() {
        beforeEach(function() {
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null
            });
            widget.render();
        });

        it('create the widget', function() {
            expect(widget.$('.g-datetime-widget').length).toBe(1);
        });

        it('create multiple widgets', function() {
            var widget2 = new girder.views.widgets.DateTimeWidget({
                parentView: null
            });
            widget2.render();

            expect(widget.$('.g-datetime-widget').length).toBe(1);
            expect(widget2.$('.g-datetime-widget').length).toBe(1);
        });

        it('default initialization', function() {
            expect(widget.$('.g-datetime-widget').length).toBe(1);
            expect(widget.date()).toBeNull();
            expect(widget.dateString().length).toBe(0);
        });
    });

    describe('custom construction', function() {
        it('default date', function() {
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null,
                defaultDate: '2015-02-01T12:00Z'
            });
            widget.render();

            expect(widget.date()).not.toBeNull();
            expect(widget.date().isSame(moment('2015-02-01T12:00Z'))).toBe(true);
        });

        it('null default date', function() {
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null,
                defaultDate: null
            });
            widget.render();

            expect(widget.date()).toBeNull();
        });

        it('blank default date', function() {
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null,
                defaultDate: ''
            });
            widget.render();

            expect(widget.date()).toBeNull();
        });

        it('without icon', function() {
            var parent = $('body').append('<div></div>');
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null,
                el: parent,
                showIcon: false
            });
            widget.render();

            expect(widget.$('.icon-calendar').length).toBe(0);

            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);
            widget.$('input').focus();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(1);
        });

        it('with icon', function() {
            var parent = $('body').append('<div></div>');
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null,
                el: parent,
                showIcon: true
            });
            widget.render();

            expect(widget.$('.icon-calendar').length).toBe(1);

            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);
            widget.$('.icon-calendar').click();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(1);
        });
    });

    describe('set/get date', function() {
        beforeEach(function() {
            widget = new girder.views.widgets.DateTimeWidget({
                parentView: null
            });
            widget.render();
        });

        it('set date from ISO 8601 string in UTC', function() {
            widget.setDate('2015-02-01T12:00Z');
            expect(widget.date()).not.toBeNull();
            expect(widget.date().isSame(moment('2015-02-01T12:00Z'))).toBe(true);
        });

        it('set date from ISO 8601 string with UTC offset', function() {
            widget.setDate('2015-02-01T12:00-05:00');
            expect(widget.date()).not.toBeNull();
            expect(widget.date().isSame(moment('2015-02-01T17:00Z'))).toBe(true);
        });

        it('set date from string without time', function() {
            widget.setDate('2015-02-01');
            expect(widget.date()).not.toBeNull();
            expect(widget.date().isSame(moment('2015-02-01T00:00Z'))).toBe(true);
        });

        it('set date from object in UTC', function() {
            widget.setDate(moment('2015-03-01T12:00Z'));
            expect(widget.date()).not.toBeNull();
            expect(widget.date().isSame(moment('2015-03-01T12:00Z'))).toBe(true);
        });

        it('set date from object with UTC offset', function() {
            widget.setDate(moment('2015-03-01T12:00-05:00'));
            expect(widget.date()).not.toBeNull();
            expect(widget.date().isSame(moment('2015-03-01T17:00Z'))).toBe(true);
        });

        it('clear date with null', function() {
            widget.setDate(moment());
            expect(widget.date()).not.toBeNull();
            widget.setDate(null);
            expect(widget.date()).toBeNull();
        });

        it('clear date with empty string', function() {
            widget.setDate(moment());
            expect(widget.date()).not.toBeNull();
            widget.setDate('');
            expect(widget.date()).toBeNull();
        });

        it('get date as string when set in UTC', function() {
            widget.setDate('2015-02-01T12:00Z');
            expect(widget.dateString()).toBe('2015-02-01T12:00:00+00:00');
        });

        it('get date as string when set with UTC offset', function() {
            widget.setDate('2015-02-01T12:00-05:00');
            expect(widget.dateString()).toBe('2015-02-01T17:00:00+00:00');
        });

        it('get date as string when not set', function() {
            expect(widget.date()).toBeNull();
            expect(widget.dateString()).toBe('');
        });
    });
});

describe('Test DateTimeRangeWidget', function() {
    var widget;

    describe('default construction', function() {
        beforeEach(function() {
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null
            });
            widget.render();
        });

        it('create the widget', function() {
            expect(widget.$('.g-datetime-widget-from').length).toBe(1);
            expect(widget.$('.g-datetime-widget-to').length).toBe(1);
        });

        it('create multiple widgets', function() {
            var widget2 = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null
            });
            widget2.render();

            expect(widget.$('.g-datetime-widget-from').length).toBe(1);
            expect(widget.$('.g-datetime-widget-to').length).toBe(1);
            expect(widget2.$('.g-datetime-widget-from').length).toBe(1);
            expect(widget2.$('.g-datetime-widget-to').length).toBe(1);
        });

        it('default initialization', function() {
            expect(widget.$('.g-datetime-widget-from').val().length).toBe(0);
            expect(widget.$('.g-datetime-widget-to').val().length).toBe(0);
            expect(widget.fromDate()).toBeNull();
            expect(widget.toDate()).toBeNull();
            expect(widget.fromDateString().length).toBe(0);
            expect(widget.toDateString().length).toBe(0);
        });
    });

    describe('custom construction', function() {
        it('default dates', function() {
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null,
                defaultFromDate: '2015-02-01T12:00Z',
                defaultToDate: '2015-03-01T12:00Z'
            });
            widget.render();

            expect(widget.fromDate()).not.toBeNull();
            expect(widget.fromDate().isSame(moment('2015-02-01T12:00Z'))).toBe(true);
            expect(widget.toDate()).not.toBeNull();
            expect(widget.toDate().isSame(moment('2015-03-01T12:00Z'))).toBe(true);
        });

        it('null default dates', function() {
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null,
                defaultFromDate: null,
                defaultToDate: null
            });
            widget.render();

            expect(widget.fromDate()).toBeNull();
            expect(widget.toDate()).toBeNull();
        });

        it('blank default dates', function() {
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null,
                defaultFromDate: '',
                defaultToDate: ''
            });
            widget.render();

            expect(widget.fromDate()).toBeNull();
            expect(widget.toDate()).toBeNull();
        });

        it('without icon', function() {
            var parent = $('body').append('<div></div>');
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null,
                el: parent,
                showIcon: false
            });
            widget.render();

            expect(widget.$('.icon-calendar').length).toBe(0);
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);

            widget.$('input').eq(0).focus();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(1);
            widget.$('input').eq(0).blur();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);

            widget.$('input').eq(1).focus();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(1);
            widget.$('input').eq(1).blur();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);
        });

        it('with icon', function() {
            var parent = $('body').append('<div></div>');
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null,
                el: parent,
                showIcon: true
            });
            widget.render();

            expect(widget.$('.icon-calendar').length).toBe(2);
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);

            widget.$('.icon-calendar').eq(0).click();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(1);
            widget.$('.icon-calendar').eq(0).click();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);

            widget.$('.icon-calendar').eq(1).click();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(1);
            widget.$('.icon-calendar').eq(1).click();
            expect(widget.$('.bootstrap-datetimepicker-widget').length).toBe(0);
        });

        it('custom labels', function() {
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null,
                fromLabel: 'Custom From',
                toLabel: 'Custom To'
            });
            widget.render();

            expect(widget.$('label:contains("Custom From")').length).toBe(1);
            expect(widget.$('label:contains("Custom To")').length).toBe(1);
        });
    });

    describe('set/get dates', function() {
        beforeEach(function() {
            widget = new girder.views.widgets.DateTimeRangeWidget({
                parentView: null
            });
            widget.render();
        });

        it('set dates from ISO 8601 string in UTC', function() {
            widget.setFromDate('2015-02-01T12:00Z');
            expect(widget.fromDate()).not.toBeNull();
            expect(widget.fromDate().isSame(moment('2015-02-01T12:00Z'))).toBe(true);
            expect(widget.toDate()).toBeNull();

            widget.setToDate('2015-03-01T12:00Z');
            expect(widget.toDate()).not.toBeNull();
            expect(widget.toDate().isSame(moment('2015-03-01T12:00Z'))).toBe(true);
            expect(widget.fromDate().isSame(moment('2015-02-01T12:00Z'))).toBe(true);
        });

        it('set dates from ISO 8601 string with UTC offset', function() {
            widget.setFromDate('2015-02-01T12:00-05:00');
            expect(widget.fromDate()).not.toBeNull();
            expect(widget.fromDate().isSame(moment('2015-02-01T17:00Z'))).toBe(true);
            expect(widget.toDate()).toBeNull();

            widget.setToDate('2015-03-01T12:00-05:00');
            expect(widget.toDate()).not.toBeNull();
            expect(widget.toDate().isSame(moment('2015-03-01T17:00Z'))).toBe(true);
            expect(widget.fromDate().isSame(moment('2015-02-01T17:00Z'))).toBe(true);
        });

        it('set dates from string without time', function() {
            widget.setFromDate('2015-02-01');
            expect(widget.fromDate()).not.toBeNull();
            expect(widget.fromDate().isSame(moment('2015-02-01T00:00Z'))).toBe(true);
            expect(widget.toDate()).toBeNull();

            widget.setToDate('2015-03-01');
            expect(widget.toDate()).not.toBeNull();
            expect(widget.toDate().isSame(moment('2015-03-01T00:00Z'))).toBe(true);
            expect(widget.fromDate().isSame(moment('2015-02-01T00:00Z'))).toBe(true);
        });

        it('set dates from object in UTC', function() {
            widget.setFromDate(moment('2015-03-01T12:00Z'));
            expect(widget.fromDate()).not.toBeNull();
            expect(widget.fromDate().isSame(moment('2015-03-01T12:00Z'))).toBe(true);
            expect(widget.toDate()).toBeNull();

            widget.setToDate(moment('2015-04-01T12:00Z'));
            expect(widget.toDate()).not.toBeNull();
            expect(widget.toDate().isSame(moment('2015-04-01T12:00Z'))).toBe(true);
            expect(widget.fromDate().isSame(moment('2015-03-01T12:00Z'))).toBe(true);
        });

        it('set dates from object with UTC offset', function() {
            widget.setFromDate(moment('2015-03-01T12:00-05:00'));
            expect(widget.fromDate()).not.toBeNull();
            expect(widget.fromDate().isSame(moment('2015-03-01T17:00Z'))).toBe(true);
            expect(widget.toDate()).toBeNull();

            widget.setToDate(moment('2015-04-01T12:00-05:00'));
            expect(widget.toDate()).not.toBeNull();
            expect(widget.toDate().isSame(moment('2015-04-01T17:00Z'))).toBe(true);
            expect(widget.fromDate().isSame(moment('2015-03-01T17:00Z'))).toBe(true);
        });

        it('clear dates with null', function() {
            widget.setFromDate(moment());
            expect(widget.fromDate()).not.toBeNull();
            widget.setFromDate(null);
            expect(widget.fromDate()).toBeNull();

            widget.setToDate(moment());
            expect(widget.toDate()).not.toBeNull();
            widget.setToDate(null);
            expect(widget.toDate()).toBeNull();
        });

        it('clear dates with empty string', function() {
            widget.setFromDate(moment());
            expect(widget.fromDate()).not.toBeNull();
            widget.setFromDate('');
            expect(widget.fromDate()).toBeNull();

            widget.setToDate(moment());
            expect(widget.toDate()).not.toBeNull();
            widget.setToDate('');
            expect(widget.toDate()).toBeNull();
        });

        it('get dates as string when set in UTC', function() {
            widget.setFromDate('2015-02-01T12:00Z');
            expect(widget.fromDateString()).toBe('2015-02-01T12:00:00+00:00');

            widget.setToDate('2015-03-01T12:00Z');
            expect(widget.toDateString()).toBe('2015-03-01T12:00:00+00:00');
        });

        it('get dates as string when set with UTC offset', function() {
            widget.setFromDate('2015-02-01T12:00-05:00');
            expect(widget.fromDateString()).toBe('2015-02-01T17:00:00+00:00');

            widget.setToDate('2015-03-01T12:00-05:00');
            expect(widget.toDateString()).toBe('2015-03-01T17:00:00+00:00');
        });

        it('get dates as string when not set', function() {
            expect(widget.fromDate()).toBeNull();
            expect(widget.fromDateString()).toBe('');

            expect(widget.toDate()).toBeNull();
            expect(widget.toDateString()).toBe('');
        });

        it('enforce valid range when set from date first', function() {
            widget.setFromDate('2015-01-01');
            widget.setToDate('2014-12-01');
            expect(widget.fromDate().isSame(moment.utc('2015-01-01'))).toBe(true);
            expect(widget.toDate()).toBeNull();
        });

        it('enforce valid range when set to date first', function() {
            widget.setToDate('2014-12-01');
            widget.setFromDate('2015-01-01');
            // This automatically populates "to" date, but perhaps that's not
            // desirable.
            expect(widget.toDate().isSame(moment.utc('2014-12-01'))).toBe(true);
            expect(widget.fromDate().isSame(moment.utc('2014-12-01'))).toBe(true);
        });
    });
});
