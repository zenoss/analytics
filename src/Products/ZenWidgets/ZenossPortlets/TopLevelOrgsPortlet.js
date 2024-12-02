var TopLevelOrgsPortlet = YAHOO.zenoss.Subclass.create(
    YAHOO.zenoss.portlet.Portlet);
TopLevelOrgsPortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.TopLevelOrgsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('toplevelorgs');
        title = 'title' in args? args.title: "Root Organizers",
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource({
                method:'GET',
                url:'/zport/getRootOrganizerInfo',
                queryArguments: {'dataRoot':'Devices'} });
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime: 60;
        rootOrganizer = 'rootOrganizer' in args?args.rootOrganizer:'Devices';
        this.superclass.__init__(
            {id:id, 
             title:title,
             datasource:datasource,
             refreshTime: refreshTime,
             bodyHeight: bodyHeight
            }
        );
        this.buildSettingsPane();
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        orgs = ["Devices", "Locations", "Systems", "Groups"];
        getopt = method(this, function(x) { 
            opts = {'value':x};
            dataRoot = this.datasource.queryArguments.dataRoot;
            if (dataRoot==x) opts['selected']=true;
            return OPTION(opts, x); });
        options = map(getopt, orgs);
        this.orgselect = new SELECT(null,options);
        mycontrol = DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Root Organizer'),
                 this.orgselect
               ]);
        appendChildNodes(s, mycontrol);
    },
    submitSettings: function(e, settings) {
        var newroot = this.orgselect.value;
        this.datasource.dataRoot = newroot;
        this.superclass.submitSettings(e, {'queryArguments':
            {'dataRoot':newroot}
        });
    }
}
YAHOO.zenoss.portlet.TopLevelOrgsPortlet = TopLevelOrgsPortlet;

