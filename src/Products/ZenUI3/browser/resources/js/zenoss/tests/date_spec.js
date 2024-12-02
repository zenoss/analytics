
/* These tests assume the following:
 *
 *  Zenoss.USER_DATE_FORMAT = 'YYYY-MM-DD';
 *  Zenoss.USER_TIME_FORMAT = 'hh:mm:ss a';
 *  Zenoss.USER_TIMEZONE = 'Singapore';
 *
 */
describe('Zenoss.date', function(){
    it('formatWithTimezone applies user format and timezone', function(){
        expect(
            Zenoss.date.renderWithTimeZone(1)
        ).toBe('1970-01-01 07:30:01 am SGT');
    });

    it('formatWithTimezone handles epoc 0', function(){
        expect(
            Zenoss.date.renderWithTimeZone(0)
        ).toBe('1970-01-01 07:30:00 am SGT');
    });

    it('formatWithTimezone applies given format', function(){
        expect(
            Zenoss.date.renderWithTimeZone(1, 'YYYY.MM.DD.hh.mm.ss')
        ).toBe('1970.01.01.07.30.01');
    });

    it('formats Date objects properly', function(){
        var extdate = new Date('1/10/2017 03:05:07 PM GMT-0600')
        expect(
            Zenoss.date.renderWithTimeZone(extdate)
        ).toBe('2017-01-11 05:05:07 am SGT')
    });


describe('Moment', function() {
    beforeEach(function(){
        this.cmp = Ext.create('Zenoss.date.Moment');
    });

    it('momentFormat has correct value', function() {
        expect(
            this.cmp.momentFormat
        ).toBe(
            'YYYY-MM-DD hh:mm:ss a'
        )
    });

    it('extFormat has correct value', function() {
        expect(
            this.cmp.extFormat
        ).toBe(
            'Y-m-d h:i:s A'
        )
    });

    it('momentFormat has correct value when dateOnly is set', function() {
        var moment = Ext.create('Zenoss.date.Moment', {dateOnly: true});
        expect(
            moment.momentFormat
        ).toBe(
            'YYYY-MM-DD'
        )
    });

    it('extFormat has correct value when dateOnly is set', function() {
        var moment = Ext.create('Zenoss.date.Moment', {dateOnly: true});
        expect(
            moment.extFormat
        ).toBe(
            'Y-m-d'
        )
    });

    describe('now', function() {
        it('returns a momentjs object', function() {
            expect(moment.isMoment(Zenoss.date.Moment.now())).toBe(true);
        });

        it('returns a momentjs object with correct timezone', function() {
            expect(
                Zenoss.date.Moment.now().tz()
            ).toBe(
                Zenoss.USER_TIMEZONE
            );
        });
    });

    describe('tzstring', function() {
        it('has the correct value', function() {
            expect(Zenoss.date.Moment.tzstring).toBe('SGT');
        });
    });

    describe('asMoment', function(){
        it('accepts second timestamps', function() {
            var seconds = moment.tz(
                '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
            ).valueOf() / 1000;
            expect(
                this.cmp.asMoment(seconds).format('YYYY-MM-DD HH:mm:ss')
            ).toBe(
                '2005-03-15 21:35:12'
            );
        });
        it('accepts Javascript Date objects', function() {
            var dt = new Date(2005, 2, 15, 21, 35, 12);
            expect(
                this.cmp.asMoment(dt).format('YYYY-MM-DD HH:mm:ss')
            ).toBe(
                '2005-03-15 21:35:12'
            )
        });
        it('accepts formatted string primitives', function() {
            var dtstr = '2005-02-13 05:30:15 pm';
            expect(
                this.cmp.asMoment(dtstr).format('YYYY-MM-DD HH:mm:ss')
            ).toBe(
                '2005-02-13 17:30:15'
            )
        });
        it('accepts formatted String objects', function() {
            var dtstr = new String('2005-02-13 05:30:15 pm');
            expect(
                this.cmp.asMoment(dtstr).format('YYYY-MM-DD HH:mm:ss')
            ).toBe(
                '2005-02-13 17:30:15'
            )
        });
        it('accepts other momentjs objects', function() {
            var m = moment.tz('2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE);
            expect(
                this.cmp.asMoment(m).isSame(m)
            ).toBe(
                true
            )
        });
        it('returns a momentjs object', function() {
            expect(
                moment.isMoment(this.cmp.asMoment(Date.now()))
            ).toBe(
                true
            )
        });
        it('returns a momentjs with correct timezone', function() {
            expect(
                this.cmp.asMoment(Date.now()).tz()
            ).toBe(
                Zenoss.USER_TIMEZONE
            )
        });
        it('returns null for no args', function() {
            expect(this.cmp.asMoment()).toBe(null);
        });

        it('returns null for unsupported argument types', function() {
            expect(this.cmp.asMoment([1,2,3])).toBe(null);
            expect(this.cmp.asMoment({})).toBe(null);
        });
    });
    describe('asDateTimeString', function() {
        it('accepts momentjs objects', function() {
            var ts = moment.tz('2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE);
            expect(
                this.cmp.asDateTimeString(ts)
            ).toBe(
                '2005-03-15 09:35:12 pm'
            )
        });

        it('accepts Javascript Date objects', function() {
            var dt = new Date(2005, 2, 15, 21, 35, 12);
            expect(
                this.cmp.asDateTimeString(dt)
            ).toBe(
                '2005-03-15 09:35:12 pm'
            )
        });

        it('accepts formatted string primitives', function() {
            var dtstr = '2005-03-15 09:30:15 pm';
            expect(
                this.cmp.asDateTimeString(dtstr)
            ).toBe(
                '2005-03-15 09:30:15 pm'
            )
        });

        it('accepts formatted String objects', function() {
            var dtstr = new String('2005-03-15 09:30:15 pm');
            expect(
                this.cmp.asDateTimeString(dtstr)
            ).toBe(
                '2005-03-15 09:30:15 pm'
            )
        });

        it('accepts timestamps in seconds', function() {
            var seconds = moment.tz(
                '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
            ).valueOf() / 1000;
            expect(
                this.cmp.asDateTimeString(seconds)
            ).toBe(
                '2005-03-15 09:35:12 pm'
            );
        });

        it('returns only the date when dateOnly is true', function() {
            var cmp = Ext.create('Zenoss.date.Moment', {dateOnly: true}),
                seconds = moment.tz(
                    '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
                ).valueOf() / 1000;
            expect(
                cmp.asDateTimeString(seconds)
            ).toBe(
                '2005-03-15'
            );
        });

        it('returns null for no arguments', function() {
            expect(
                this.cmp.asDateTimeString()
            ).toBe(
                null
            );
        });
    });
});

describe('Zenoss.form.field.DateTime', function() {
    beforeEach(function(){
        this.date_string = '2005-02-13 05:30:15 pm';
        this.cmp = Ext.create('Zenoss.form.field.DateTime');
    });

    it('momentFormat has correct value', function() {
        expect(
            this.cmp.momentFormat
        ).toBe(
            'YYYY-MM-DD hh:mm:ss a'
        )
    });

    it('extFormat has correct value', function() {
        expect(
            this.cmp.extFormat
        ).toBe(
            'Y-m-d h:i:s A'
        )
    });

    it('format has correct value', function() {
        expect(
            this.cmp.format
        ).toBe(
            'Y-m-d h:i:s A'
        )
    });

    it('momentFormat has correct value when dateOnly is set', function() {
        var moment = Ext.create('Zenoss.form.field.DateTime', {dateOnly: true});
        expect(
            moment.momentFormat
        ).toBe(
            'YYYY-MM-DD'
        )
    });

    it('extFormat has correct value when dateOnly is set', function() {
        var moment = Ext.create('Zenoss.form.field.DateTime', {dateOnly: true});
        expect(
            moment.extFormat
        ).toBe(
            'Y-m-d'
        )
    });

    describe('setValue', function() {
        beforeEach(function(){
            // expected_value is 1108287015 seconds since Epoch
            this.expected_value = moment.tz(
                this.date_string, 'YYYY-MM-DD hh:mm:ss a', Zenoss.USER_TIMEZONE)
                .unix()
        });

        it('accepts Javascript Date objects', function() {
            expect(
                this.cmp.setValue(new Date(this.date_string)).getValue()
            ).toBe(
                this.expected_value
            )
        });
        it('accepts formatted string primitives', function() {
            expect(
                this.cmp.setValue(this.date_string).getValue()
            ).toBe(
                this.expected_value
            )
        });
        it('accepts formatted String objects', function() {
            expect(
                this.cmp.setValue(this.date_string).getValue()
            ).toBe(
                this.expected_value
            )
        });
        it('accepts timestamps in seconds', function() {
            var seconds = moment.tz(
                '2005-03-15 21:35:12', 'YYYY-MM-DD HH:mm:ss', Zenoss.USER_TIMEZONE
            ).unix();
            expect(
                this.cmp.setValue(seconds).getValue()
            ).toBe(
                seconds
            )
        });
        it('accepts momentjs objects', function() {
            var m = moment.tz(this.date_string, 'YYYY-MM-DD hh:mm:ss a', Zenoss.USER_TIMEZONE);
            expect(
                this.cmp.setValue(m).getValue()
            ).toBe(
                this.expected_value
            )
        });
        it('accepts no arguments', function() {
            var seconds = this.cmp.setValue().getValue();
            expect(
                seconds === undefined || seconds === null
            ).toBe(
                true
            )
        });
    });


    it('getValue returns seconds', function() {
        var seconds = this.cmp.getValue(),
            withSeconds = moment(seconds * 1000).format('YYYY-mm-dd HH:mm:ss'),
            withoutSeconds = moment.unix(seconds).format('YYYY-mm-dd HH:mm:ss');
        expect(
            withSeconds == withoutSeconds
        ).toBe(
            true
        )
    });

    it('getSubmitValue returns seconds', function() {
        var seconds = this.cmp.getSubmitValue(),
            withSeconds = moment(seconds * 1000).format('YYYY-mm-dd HH:mm:ss'),
            withoutSeconds = moment.unix(seconds).format('YYYY-mm-dd HH:mm:ss');
        expect(
            withSeconds == withoutSeconds
        ).toBe(
            true
        )
    });
});
});
