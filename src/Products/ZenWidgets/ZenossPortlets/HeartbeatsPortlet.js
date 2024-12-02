var HeartbeatsPortlet = Subclass.create(YAHOO.zenoss.portlet.Portlet);
HeartbeatsPortlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.HeartbeatsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('heartbeats');
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource(
            {'url':'/zport/dmd/ZenEventManager/getHeartbeatIssuesJSON'});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight :
            200;
        title = 'title' in args? args.title:"Daemon Processes Down";
        refreshTime = 'refreshTime' in args? args.refreshTime : 60;
        this.superclass.__init__(
            {id:id,
             title:title,
             datasource:datasource,
             bodyHeight: bodyHeight,
             refreshTime: refreshTime
            }
        );
    }
}
YAHOO.zenoss.portlet.HeartbeatsPortlet = HeartbeatsPortlet;
