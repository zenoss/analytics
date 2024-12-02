describe("Zenoss.render.date Test Suite", function(){
    beforeEach(function(){
        Zenoss.USER_DATE_FORMAT = "YYYY-MM-DD";
        Zenoss.USER_TIME_FORMAT = "hh:mm:ss a";
        Zenoss.USER_TIMEZONE = "Singapore";
    });

    it('render.date applies user format and timezone', function(){
        expect(
            Zenoss.render.date(1)
        ).toBe("1970-01-01 07:30:01 am SGT");
    });

    it('render.date handles epoc 0', function(){
        expect(
            Zenoss.render.date(0)
        ).toBe("1970-01-01 07:30:00 am SGT");
    });

    it('render.date applies given format', function(){
        expect(
            Zenoss.render.date(1, 'YYYY.MM.DD.hh.mm.ss')
        ).toBe("1970.01.01.07.30.01");
    });

    it('render.date handles Date objects properly', function(){
        var extdate = new Date('1/10/2017 03:05:07 PM GMT-0600')
        expect(
            Zenoss.render.date(extdate)
        ).toBe('2017-01-11 05:05:07 am SGT')
    });
});

describe('Zenoss.render.PropertyPath Test Suite', function() {
    it('render.PropertyPath renders /zport/dmd/Devices as /', function() {
        expect(
            Zenoss.render.PropertyPath('/zport/dmd/Devices')
        ).toBe(
            '/'
        );
    });

    it('render.PropertyPath removes /zport/dmd/Devices from path', function() {
        expect(
            Zenoss.render.PropertyPath('/zport/dmd/Devices/Server/Linux')
        ).toBe(
            '/Server/Linux'
        );
    });

    it('render.PropertyPath accepts paths without /zport/dmd/Devices starting the path', function() {
        expect(
            Zenoss.render.PropertyPath('/Server/Linux')
        ).toBe(
            '/Server/Linux'
        );
    });

    it('render.PropertyPath accepts paths without /zport/dmd starting the path', function() {
        expect(
            Zenoss.render.PropertyPath('/Devices/Server/Linux')
        ).toBe(
            '/Server/Linux'
        );
    });

    it('render.PropertyPath accepts paths without /zport starting the path', function() {
        expect(
            Zenoss.render.PropertyPath('/dmd/Devices/Server/Linux')
        ).toBe(
            '/Server/Linux'
        );
    });
});
