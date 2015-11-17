describe('Test DateTimeWidget', function() {
    var widget;

    beforeEach(function() {
        $('body').off();

        widget = new girder.views.DateTimeWidget({
            parentView: null,
            el: 'body',
            prefix: 'test'
        });
        widget.render();
    });

    it('create the widget', function() {
        expect($('input#test-datetime').length).toBe(1);
    });

    it('default initialization', function() {
        expect($('input#test-datetime').val().length).toBe(0);
        expect(widget.date()).toBeNull();
        expect(widget.dateString().length).toBe(0);
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

describe('Test DateTimeRangeWidget', function() {
    var widget;

    beforeEach(function() {
        $('body').off();

        widget = new girder.views.DateTimeRangeWidget({
            parentView: null,
            el: 'body',
            prefix: 'test'
        });
        widget.render();
    });

    it('create the widget', function() {
        expect($('input#test-datetime-from').length).toBe(1);
        expect($('input#test-datetime-to').length).toBe(1);
    });

    it('default initialization', function() {
        expect($('input#test-datetime-from').val().length).toBe(0);
        expect($('input#test-datetime-to').val().length).toBe(0);
        expect(widget.fromDate()).toBeNull();
        expect(widget.toDate()).toBeNull();
        expect(widget.fromDateString().length).toBe(0);
        expect(widget.toDateString().length).toBe(0);
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
