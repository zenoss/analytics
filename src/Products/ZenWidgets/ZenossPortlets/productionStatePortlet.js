var ProdStatePortlet = YAHOO.zenoss.Subclass.create(
    YAHOO.zenoss.portlet.Portlet);
ProdStatePortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.ProdStatePortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('ProdState');
        title = 'title' in args? args.title: "Production States";
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource({
                method:'GET',
                url:'/zport/dmd/ZenEventManager/getDevProdStateJSON',
                queryArguments: {'prodStates':['Maintenance','Testing']} });
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime: 60;
        prodStates = 'prodStates' in args?args.prodStates:
            ['Maintenance','Testing'];
        this.superclass.__init__(
            {id:id, 
             title:title,
             datasource:datasource,
             refreshTime: refreshTime,
             bodyHeight: bodyHeight
            }
        );
        this.datasource.widths = {'Prod State':'100px'};
        this.buildSettingsPane();
    },
    buildSettingsPane: function() {
        s = this.settingsSlot;
        var getopt = method(this, function(x) { 
            opts = {'value':x};
            prodStates = this.datasource.queryArguments.prodStates;
            if (findValue(prodStates, x)>-1) opts['selected']=true;
            return OPTION(opts, x); });
        this.orgselect = SELECT({'multiple':true},null);
        var createOptions = method(this, function(jsondoc) {
            forEach(jsondoc, method(this, function(x) {
                opt = getopt(x[0]);
                appendChildNodes(this.orgselect, opt);
            }));
        });
        mycontrol = DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Production States'),
                 this.orgselect
               ]);
        appendChildNodes(s, mycontrol);
        d = loadJSONDoc('/zport/dmd/getProdStateConversions');
        d.addCallback(method(this, createOptions));
    },
    submitSettings: function(e, settings) {
        var newstates = [];
        forEach(this.orgselect.options, function(x) {
            if (x.selected) newstates.push(x.value);
        });
        this.datasource.queryArguments.prodStates = newstates;
        this.superclass.submitSettings(e, {'queryArguments':
            {'prodStates':newstates}
        });
    }
}
YAHOO.zenoss.portlet.ProdStatePortlet = ProdStatePortlet;
