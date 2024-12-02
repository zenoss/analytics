var WatchListPortlet = YAHOO.zenoss.Subclass.create(YAHOO.zenoss.portlet.Portlet);

WatchListPortlet.prototype = {
    __class__:"YAHOO.zenoss.portlet.WatchListPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('watchlist');
        title = 'title' in args? args.title: "Object Watch List",
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource({
                useRandomParameter: false,
                url:'/zport/dmd/ZenEventManager/getEntityListEventSummary',
                method:'POST',
                postContent: ['/Devices/Discovered']});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime: 60;
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
        this.locsearch = new YAHOO.zenoss.zenautocomplete.DevAndEventObjectSearch(
            'Zenoss Objects', s);
        addElementClass(this.locsearch.container, 'portlet-settings-control');
        addElementClass(this.locsearch.container, 'watch-list-objects');         
    },
    submitSettings: function(e, settings) {
        var postContent = settings?settings.postContent:
                          this.datasource.postContent;
        var newob = this.locsearch.input.value;
        if (findValue(postContent, newob)<0) {
            if (newob.length>0) postContent.push(newob);
            this.superclass.submitSettings(e, {'postContent':postContent});
        }
        this.locsearch.input.value = '';
    },
    fillTable: function(contents) {
        var columnDefs = contents.columnDefs;
        var dataSource = contents.dataSource;
        i=0;
        forEach(dataSource.liveData, bind(function(x){
            var removelink = "<a id='"+this.id+"_row_"+i+
                         "' class='removerowlink'"+
                         " title='Stop watching this object'>" +
                         "X</a>";
            x['Object'] = removelink + x['Object'];
            i++;
        }, this));
        var oConfigs = {};
        addElementClass(this.body, 'yui-skin-sam');
        if (this.dataTable) {
            oRequest = {'results':dataSource.liveData}
            this.dataTable.onDataReturnInitializeTable(null, oRequest);
        } else {
            var myDataTable = new YAHOO.widget.DataTable(
                this.body.id, columnDefs, dataSource, oConfigs);
            this.dataTable = myDataTable;
        }
        forEach(this.dataTable.getRecordSet().getRecords(), bind(function(x){
            var row = this.dataTable.getTrEl(x);
            var link = getElementsByTagAndClassName('a','removerowlink',row)[0];
            connect(link, "onclick", method(this, 
                function(){this.deleteRow(x);}));
        }, this));
    },
    deleteRow: function(record) {
        var data = record.getData()['Object'];
        var name = regex = data.match(/<\/div>(.*?)<\/a>/)[1];
        myarray = this.datasource.postContent;
        myarray.splice(findValue(myarray, name), 1);
        this.submitSettings(null, {'postContent':myarray});
    }
}
YAHOO.zenoss.portlet.WatchListPortlet = WatchListPortlet;
