var GoogleMapsDatasource = Class.create();

GoogleMapsDatasource.prototype = {
    __class__ : "YAHOO.zenoss.portlet.GoogleMapsDatasource",
    __init__: function(settings) {
        this.polling = settings.polling;
        this.baseLoc = settings.baseLoc;
    },
    get: function(callback) {
        this.callback = callback;
        var url = '/zport/dmd' + escape(this.baseLoc) +
                  '/simpleLocationGeoMap?polling='+this.polling;
        html = '<iframe src="' + url + '" ' +
               'style="border:medium none;margin:-2px 0px;padding:0px;'+
               'overflow:hidden;width:100%;height:100%;"/>';
        callback({responseText:html});
    }
}
YAHOO.zenoss.portlet.GoogleMapsDatasource = GoogleMapsDatasource;

var GoogleMapsPortlet = YAHOO.zenoss.Subclass.create(
    YAHOO.zenoss.portlet.Portlet);
GoogleMapsPortlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.GoogleMapsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('googlemaps');
        baseLoc = 'baseLoc' in args? args.baseLoc : '/Locations';
        bodyHeight = 'bodyHeight' in args? args.bodyHeight : 400;
        title = 'title' in args? args.title: "Locations";
        refreshTime = 'refreshTime' in args? args.refreshTime : 60;
        polling = 'polling' in args? args.polling : 400;
        this.mapobject = null;
        var datasource = 'datasource' in args?
            args.datasource:
            new YAHOO.zenoss.portlet.GoogleMapsDatasource(
                {   'baseLoc':baseLoc?baseLoc:'/Locations',
                    'polling':polling?polling:400
                });
        this.superclass.__init__(
            {id:id, title:title, polling:polling, refreshTime:refreshTime,
            datasource:datasource, bodyHeight:bodyHeight}
        );
        this.buildSettingsPane();
        this.hardRefreshTime = (60*60)-2; // Once every 59mins58secs
        callLater(this.hardRefreshTime, this.force_reload);
    },
    force_reload: function() {
        YAHOO.zenoss.setInnerHTML(this.body, this.body.innerHTML)
        callLater(this.hardRefreshTime, this.force_reload);
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        this.locsearch = YAHOO.zenoss.zenautocomplete.LocationSearch(
            'Base Location', s);
        addElementClass(this.locsearch.container,
                        'portlet-settings-control'); 
        this.rateinput = INPUT({'value': this.datasource.polling?this.datasource.polling:400}, []);        
        var container = DIV({
            'class':'portlet-settings-control'
        }, [
            DIV({'class':'control-label'}, 'Geocode Polling Rate'),
            this.rateinput
           ]
        );
        s.appendChild(container);  
    },
    submitSettings: function(e, settings) {
        baseLoc = this.locsearch.input.value;
        polling = this.rateinput.value;
        if (baseLoc.length<1) baseLoc = this.datasource.baseLoc;
        this.locsearch.input.value = '';       
        if (!parseInt(polling)) polling = this.datasource.polling; 
        this.superclass.submitSettings(e, {'baseLoc':baseLoc, 'polling':polling});
    },
    startRefresh: function(firsttime) {
        if (!firsttime) this.mapobject.refresh();
        if (this.refreshTime>0)
            this.calllater = callLater(this.refreshTime, this.startRefresh);
    }

}
YAHOO.zenoss.portlet.GoogleMapsPortlet = GoogleMapsPortlet;

