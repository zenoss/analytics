var SiteWindowDatasource = Class.create();

SiteWindowDatasource.prototype = {
    __class__ : "YAHOO.zenoss.portlet.SiteWindowDatasource",
    __init__: function(settings) {
        this.baseLoc = settings.baseLoc;
    },
    get: function(callback) {
        this.callback = callback;
		var url = this.baseLoc;
        if (url == YAHOO.zenoss.portlet.DEFAULT_SITEWINDOW_URL) {
            url += '?v=' + YAHOO.zenoss.ZENOSS_VERSION + '&p=' + YAHOO.zenoss.ZENOSS_PRODUCT;
        }
        var html = '<iframe src="' + url + '" ' +
            'style="border:medium none;margin:0;padding:0;'+
            'background-color:#fff;'+
            'width:100%;height:100%;"/>';
        callback({responseText:html});
    }
}
YAHOO.zenoss.portlet.SiteWindowDatasource = SiteWindowDatasource;

var SiteWindowPortlet = YAHOO.zenoss.Subclass.create(
    YAHOO.zenoss.portlet.Portlet);
SiteWindowPortlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.SiteWindowPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('sitewindow');
        baseLoc = 'baseLoc' in args? args.baseLoc : YAHOO.zenoss.portlet.DEFAULT_SITEWINDOW_URL;
        bodyHeight = 'bodyHeight' in args? args.bodyHeight : 400;
        title = 'title' in args? args.title: "Site Window";
        refreshTime = 'refreshTime' in args? args.refreshTime : 60;
        miscthing = 'miscthing' in args? args.miscthing: "miscthing";
        this.mapobject = null;
        var datasource = 'datasource' in args? 
            args.datasource:
            new YAHOO.zenoss.portlet.SiteWindowDatasource(
                {'baseLoc':baseLoc?baseLoc:''});
        this.superclass.__init__(
            {id:id, title:title, refreshTime:refreshTime, miscthing:miscthing,
            datasource:datasource, bodyHeight:bodyHeight}
        );
        this.buildSettingsPane();
        setStyle(this.body, {'overflow-y':'hidden'});
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        /*
        this.locsearch = YAHOO.zenoss.zenautocomplete.LocationSearch(
            'URL (http://www.zenoss.com)', s);
        */
        this.locsearch = INPUT({'value':this.datasource.baseLoc}, []);
        var container = DIV({
            'class':'autocompleter-container portlet-settings-control'
        }, [
            DIV({'class':'control-label'}, 'URL (http://www.zenoss.com)'),
            this.locsearch
           ]
        );
        s.appendChild(container);
    },
    submitSettings: function(e, settings) {
        baseLoc = this.locsearch.value;
        if (/^https?\:\/\//.test(baseLoc)) {
            if (baseLoc.length<1) baseLoc = this.datasource.baseLoc;
            this.superclass.submitSettings(e, {'baseLoc':baseLoc});
        } else {
            alert('malformed url, please specify a protocol');
        }
    },
    startRefresh: function(firsttime) {
        if (!firsttime) this.datasource.get(this.fill);
        if (this.refreshTime>0)
            this.calllater = callLater(this.refreshTime, this.startRefresh);
    }

}
YAHOO.zenoss.portlet.SiteWindowPortlet = SiteWindowPortlet;
