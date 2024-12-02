var DeviceIssuesPortlet = Subclass.create(YAHOO.zenoss.portlet.Portlet);
DeviceIssuesPortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.DeviceIssuesPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('devissues');
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource(
            {'url':'/zport/dmd/ZenEventManager/getDeviceIssuesJSON'});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight :
            200;
        title = 'title' in args? args.title:"Device Issues";
        refreshTime = 'refreshTime' in args? args.refreshTime : 60;
        this.superclass.__init__(
            {id:id, title:title, 
             datasource:datasource, 
             refreshTime: refreshTime,
             bodyHeight:bodyHeight}
        );
    }
}
YAHOO.zenoss.portlet.DeviceIssuesPortlet = DeviceIssuesPortlet;
